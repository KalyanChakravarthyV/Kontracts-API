from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Tuple
import numpy as np
from sqlalchemy.orm import Session

from app.models.lease import Lease, LeaseScheduleEntry, LeaseClassification
from app.models.schedule import ASC842Schedule


class ASC842Calculator:
    """
    ASC 842 Lease Accounting Calculator

    ASC 842 requires lessees to recognize:
    - Right-of-Use (ROU) Asset
    - Lease Liability

    Operating Leases: Straight-line expense recognition
    Finance Leases: Interest + amortization expense recognition
    """

    def __init__(self, lease: Lease):
        self.lease = lease

    def calculate_payment_periods(self) -> int:
        """Calculate number of payment periods based on frequency"""
        frequency_map = {
            "monthly": self.lease.lease_term_months,
            "quarterly": self.lease.lease_term_months // 3,
            "annual": self.lease.lease_term_months // 12,
        }
        return frequency_map.get(self.lease.payment_frequency, self.lease.lease_term_months)

    def calculate_period_rate(self) -> Decimal:
        """Calculate periodic interest rate from annual IBR"""
        annual_rate = self.lease.incremental_borrowing_rate
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

        # Present value of annuity formula: PMT * [(1 - (1 + r)^-n) / r]
        if period_rate == 0:
            pv = Decimal(str(payment * n_periods))
        else:
            pv_factor = (1 - (1 + period_rate) ** -n_periods) / period_rate
            pv = Decimal(str(payment * pv_factor))

        # Add present value of residual value
        if self.lease.residual_value > 0:
            residual_pv = float(self.lease.residual_value) / ((1 + period_rate) ** n_periods)
            pv += Decimal(str(residual_pv))

        return pv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_initial_measurements(self) -> Tuple[Decimal, Decimal]:
        """
        Calculate initial ROU asset and lease liability

        Lease Liability = PV of lease payments
        ROU Asset = Lease Liability + Initial Direct Costs + Prepaid Rent - Lease Incentives
        """
        lease_liability = self.calculate_present_value()

        rou_asset = (
            lease_liability
            + self.lease.initial_direct_costs
            + self.lease.prepaid_rent
            - self.lease.lease_incentives
        )

        return rou_asset, lease_liability

    def generate_schedule(self, db: Session) -> ASC842Schedule:
        """Generate complete ASC 842 lease schedule"""
        rou_asset, lease_liability = self.calculate_initial_measurements()
        n_periods = self.calculate_payment_periods()
        period_rate = self.calculate_period_rate()

        if self.lease.classification == LeaseClassification.FINANCE:
            entries = self._generate_finance_lease_schedule(
                rou_asset, lease_liability, n_periods, period_rate
            )
        else:
            entries = self._generate_operating_lease_schedule(
                rou_asset, lease_liability, n_periods, period_rate
            )

        # Calculate totals
        total_payments = sum(e["lease_payment"] for e in entries)
        total_interest = sum(e["interest_expense"] for e in entries)
        total_amortization = sum(e["amortization"] for e in entries)

        # Create schedule record
        schedule = ASC842Schedule(
            lease_id=self.lease.id,
            initial_rou_asset=rou_asset,
            initial_lease_liability=lease_liability,
            total_payments=total_payments,
            total_interest=total_interest,
            total_amortization=total_amortization,
            schedule_data={"entries": entries},
        )
        db.add(schedule)

        # Create schedule entries
        for entry_data in entries:
            entry = LeaseScheduleEntry(
                lease_id=self.lease.id,
                schedule_type="ASC842",
                **entry_data
            )
            db.add(entry)

        db.commit()
        db.refresh(schedule)
        return schedule

    def _generate_finance_lease_schedule(
        self, rou_asset: Decimal, lease_liability: Decimal, n_periods: int, period_rate: Decimal
    ) -> List[Dict]:
        """Generate schedule for finance lease (interest + amortization)"""
        entries = []
        remaining_liability = lease_liability
        remaining_asset = rou_asset
        amortization_per_period = (rou_asset / Decimal(str(n_periods))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        for period in range(1, n_periods + 1):
            period_date = self._calculate_period_date(period)

            # Interest expense = Beginning liability * period rate
            interest_expense = (remaining_liability * period_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Principal reduction = Payment - Interest
            principal_reduction = self.lease.periodic_payment - interest_expense

            # Ending liability = Beginning liability - Principal reduction
            ending_liability = remaining_liability - principal_reduction

            # Amortization (straight-line for finance leases)
            if period == n_periods:
                # Last period: amortize remaining balance
                amortization = remaining_asset
            else:
                amortization = amortization_per_period

            ending_asset = remaining_asset - amortization

            entries.append({
                "period": period,
                "period_date": period_date,
                "lease_payment": self.lease.periodic_payment,
                "interest_expense": interest_expense,
                "principal_reduction": principal_reduction,
                "lease_liability_beginning": remaining_liability,
                "lease_liability_ending": max(ending_liability, Decimal("0")),
                "rou_asset_beginning": remaining_asset,
                "amortization": amortization,
                "rou_asset_ending": max(ending_asset, Decimal("0")),
                "total_expense": interest_expense + amortization,
            })

            remaining_liability = max(ending_liability, Decimal("0"))
            remaining_asset = max(ending_asset, Decimal("0"))

        return entries

    def _generate_operating_lease_schedule(
        self, rou_asset: Decimal, lease_liability: Decimal, n_periods: int, period_rate: Decimal
    ) -> List[Dict]:
        """Generate schedule for operating lease (straight-line expense)"""
        entries = []
        remaining_liability = lease_liability
        remaining_asset = rou_asset

        # Calculate total lease cost and straight-line expense
        total_lease_cost = (self.lease.periodic_payment * Decimal(str(n_periods))) + self.lease.initial_direct_costs
        straight_line_expense = (total_lease_cost / Decimal(str(n_periods))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        for period in range(1, n_periods + 1):
            period_date = self._calculate_period_date(period)

            # Interest expense = Beginning liability * period rate
            interest_expense = (remaining_liability * period_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # For operating leases: Amortization = Straight-line expense - Interest
            amortization = straight_line_expense - interest_expense

            # Principal reduction = Payment - Interest
            principal_reduction = self.lease.periodic_payment - interest_expense

            # Ending liability
            ending_liability = remaining_liability - principal_reduction

            # Ending ROU asset
            ending_asset = remaining_asset - amortization

            entries.append({
                "period": period,
                "period_date": period_date,
                "lease_payment": self.lease.periodic_payment,
                "interest_expense": interest_expense,
                "principal_reduction": principal_reduction,
                "lease_liability_beginning": remaining_liability,
                "lease_liability_ending": max(ending_liability, Decimal("0")),
                "rou_asset_beginning": remaining_asset,
                "amortization": amortization,
                "rou_asset_ending": max(ending_asset, Decimal("0")),
                "total_expense": straight_line_expense,
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
