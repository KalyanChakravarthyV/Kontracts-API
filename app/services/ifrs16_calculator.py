from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session

from app.models.lease import Lease, LeaseScheduleEntry
from app.models.schedule import IFRS16Schedule
from .utils import make_json_safe


class IFRS16Calculator:
    """
    IFRS 16 Lease Accounting Calculator

    IFRS 16 eliminates the operating vs finance lease distinction for lessees.
    All leases are treated similarly to finance leases under ASC 842.

    Recognition:
    - Right-of-Use Asset (depreciated on straight-line basis)
    - Lease Liability (amortized using effective interest method)

    Expense Recognition:
    - Interest expense on lease liability (front-loaded)
    - Depreciation expense on ROU asset (straight-line)
    """

    def __init__(self, lease: Lease):
        self.lease = lease

    def calculate_term_months(self) -> int:
        """Calculate lease term in months from commencement and end dates"""
        if self.lease.end_date <= self.lease.commencement_date:
            raise ValueError("end_date must be after commencement_date")
        delta = relativedelta(self.lease.end_date, self.lease.commencement_date)
        months = delta.years * 12 + delta.months
        if delta.days > 0:
            months += 1
        if months <= 0:
            raise ValueError("Lease term must be at least one month")
        return months

    def calculate_payment_periods(self) -> int:
        """Calculate number of payment periods based on frequency"""
        term_months = self.calculate_term_months()
        frequency_map = {
            "monthly": term_months,
            "quarterly": term_months // 3,
            "annual": term_months // 12,
        }
        return frequency_map.get(self.lease.payment_frequency, term_months)

    def calculate_period_rate(self) -> Decimal:
        """Calculate periodic interest rate from annual discount rate"""
        annual_rate = self.lease.discount_rate / 100
        frequency_map = {
            "monthly": Decimal("12"),
            "quarterly": Decimal("4"),
            "annual": Decimal("1"),
        }
        periods = frequency_map.get(self.lease.payment_frequency, Decimal("12"))
        return annual_rate / periods

    def calculate_present_value(self) -> Decimal:
        """Calculate present value of lease payments"""
        n_periods = self.calculate_payment_periods()
        period_rate = float(self.calculate_period_rate())
        payment = float(self.lease.periodic_payment)

        # Present value of annuity formula
        if period_rate == 0:
            pv = Decimal(str(payment * n_periods))
        else:
            pv_factor = (1 - (1 + period_rate) ** -n_periods) / period_rate
            pv = Decimal(str(payment * pv_factor))

        # Add present value of residual value
        if self.lease.residual_value > 0:
            residual_pv = float(self.lease.residual_value) / ((1 + period_rate) ** n_periods)
            pv += Decimal(str(residual_pv))

        return pv.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    def calculate_initial_measurements(self) -> Tuple[Decimal, Decimal]:
        """
        Calculate initial ROU asset and lease liability under IFRS 16

        Lease Liability = PV of lease payments
        ROU Asset = Lease Liability + Initial Direct Costs + Prepaid Rent - Lease Incentives

        Note: IFRS 16 includes initial direct costs in ROU asset
        """
        lease_liability = self.calculate_present_value()

        rou_asset = (
            lease_liability
            + self.lease.initial_direct_costs
            + self.lease.prepaid_rent
            - self.lease.lease_incentives
        )

        return rou_asset, lease_liability

    def generate_schedule(self, db: Session) -> IFRS16Schedule:
        """Generate complete IFRS 16 lease schedule"""
        rou_asset, lease_liability = self.calculate_initial_measurements()
        n_periods = self.calculate_payment_periods()
        period_rate = self.calculate_period_rate()

        entries = self._generate_ifrs16_schedule(
            rou_asset, lease_liability, n_periods, period_rate
        )

        # Calculate totals
        total_payments = sum(e["lease_payment"] for e in entries)
        total_interest = sum(e["interest_expense"] for e in entries)
        total_depreciation = sum(e["amortization"] for e in entries)

         # Safe JSON Serializer
        entries = make_json_safe(entries)

        # Create schedule record
        schedule = IFRS16Schedule(
            lease_id=self.lease.id,
            initial_rou_asset=rou_asset,
            initial_lease_liability=lease_liability,
            total_payments=total_payments,
            total_interest=total_interest,
            total_depreciation=total_depreciation,
            schedule_data={"entries": entries},
        )
        db.add(schedule)

        # Create schedule entries
        for entry_data in entries:
            entry = LeaseScheduleEntry(
                lease_id=self.lease.id,
                schedule_type="IFRS16",
                **entry_data
            )
            db.add(entry)

        db.commit()
        db.refresh(schedule)
        return schedule

    def _generate_ifrs16_schedule(
        self, rou_asset: Decimal, lease_liability: Decimal, n_periods: int, period_rate: Decimal
    ) -> List[Dict]:
        """
        Generate IFRS 16 lease schedule

        Key differences from ASC 842:
        - No operating vs finance lease distinction
        - Depreciation is always straight-line
        - Interest expense calculated on liability balance (front-loaded)
        - Total expense is higher in early periods, lower in later periods
        """
        entries = []
        remaining_liability = lease_liability
        remaining_asset = rou_asset

        # Straight-line depreciation
        depreciation_per_period = (rou_asset / Decimal(str(n_periods))).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        )

        for period in range(1, n_periods + 1):
            period_date = self._calculate_period_date(period)

            # Interest expense = Beginning liability * discount rate (effective interest method)
            interest_expense = (remaining_liability * period_rate).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )

            # Principal reduction = Payment - Interest
            principal_reduction = self.lease.periodic_payment - interest_expense

            # Ending liability
            ending_liability = remaining_liability - principal_reduction

            # Depreciation (straight-line)
            if period == n_periods:
                # Last period: depreciate remaining balance to ensure ROU asset reaches zero
                depreciation = remaining_asset
            else:
                depreciation = depreciation_per_period

            ending_asset = remaining_asset - depreciation

            # Total expense = Interest + Depreciation
            total_expense = interest_expense + depreciation

            entries.append({
                "period": period,
                "period_date": period_date,
                "lease_payment": self.lease.periodic_payment,
                "interest_expense": interest_expense,
                "principal_reduction": principal_reduction,
                "lease_liability_beginning": remaining_liability,
                "lease_liability_ending": max(ending_liability, Decimal("0")),
                "rou_asset_beginning": remaining_asset,
                "amortization": depreciation,  # Called depreciation in IFRS 16
                "rou_asset_ending": max(ending_asset, Decimal("0")),
                "total_expense": total_expense,
            })

            remaining_liability = max(ending_liability, Decimal("0"))
            remaining_asset = max(ending_asset, Decimal("0"))

        return entries

    def _calculate_period_date(self, period: int) -> date:
        """Calculate the date for a given period"""
        frequency_map = {
            "monthly": relativedelta(months=period),
            "quarterly": relativedelta(months=period * 3),
            "annual": relativedelta(years=period),
        }
        delta = frequency_map.get(self.lease.payment_frequency, relativedelta(months=period))
        return self.lease.commencement_date + delta
