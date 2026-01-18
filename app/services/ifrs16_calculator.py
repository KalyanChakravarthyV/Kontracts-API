from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session

from app.models.lease import Lease, LeaseScheduleEntry
from app.models.schedule import IFRS16Schedule
from app.models.journals import Payments
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

    def fetch_payments_from_db(self, db: Session) -> List[Dict]:
        """Fetch payments from database for this lease"""
        payments = db.query(Payments).filter(
            Payments.contract_id == str(self.lease.id)
        ).order_by(Payments.due_date).all()

        if not payments:
            raise ValueError(f"No payments found for lease ID {self.lease.id}")

        payment_schedule = []
        for payment in payments:
            payment_schedule.append({
                "amount": Decimal(str(payment.amount)),
                "due_date": payment.due_date.date() if hasattr(payment.due_date, 'date') else payment.due_date,
                "payment_id": payment.id
            })
        return payment_schedule

    def calculate_period_rate_from_payments(self, payment_schedule: List[Dict]) -> Decimal:
        """Calculate periodic interest rate from annual discount rate and payment cadence"""
        annual_rate = self.lease.discount_rate / 100
        periods = Decimal("12")
        if len(payment_schedule) > 1:
            days_between = []
            for i in range(len(payment_schedule) - 1):
                date1 = payment_schedule[i]["due_date"]
                date2 = payment_schedule[i + 1]["due_date"]
                days = (date2 - date1).days
                if days > 0:
                    days_between.append(days)
            if days_between:
                avg_days = sum(days_between) / len(days_between)
                if avg_days <= 35:
                    periods = Decimal("12")
                elif avg_days <= 100:
                    periods = Decimal("4")
                else:
                    periods = Decimal("1")
        return annual_rate / periods

    def calculate_present_value(self, payment_schedule: List[Dict], period_rate: Decimal) -> Decimal:
        """Calculate present value of lease payments"""
        n_periods = len(payment_schedule)
        rate = float(period_rate)
        pv = Decimal("0")

        for period_num, payment in enumerate(payment_schedule, start=1):
            payment_amount = float(payment["amount"])
            if rate == 0:
                discount_factor = 1.0
            else:
                discount_factor = 1.0 / ((1.0 + rate) ** period_num)
            pv += Decimal(str(payment_amount * discount_factor))

        if self.lease.residual_value > 0:
            if rate == 0:
                pv += self.lease.residual_value
            else:
                residual_pv = float(self.lease.residual_value) / ((1.0 + rate) ** n_periods)
                pv += Decimal(str(residual_pv))

        return pv.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    def calculate_initial_measurements(
        self, payment_schedule: List[Dict], period_rate: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate initial ROU asset and lease liability under IFRS 16

        Lease Liability = PV of lease payments
        ROU Asset = Lease Liability + Initial Direct Costs + Prepaid Rent - Lease Incentives

        Note: IFRS 16 includes initial direct costs in ROU asset
        """
        lease_liability = self.calculate_present_value(payment_schedule, period_rate)

        rou_asset = (
            lease_liability
            + self.lease.initial_direct_costs
            + self.lease.prepaid_rent
            - self.lease.lease_incentives
        )

        return rou_asset, lease_liability

    def generate_schedule(self, db: Session) -> IFRS16Schedule:
        """Generate complete IFRS 16 lease schedule"""
        payment_schedule = self.fetch_payments_from_db(db)
        period_rate = self.calculate_period_rate_from_payments(payment_schedule)
        rou_asset, lease_liability = self.calculate_initial_measurements(
            payment_schedule, period_rate
        )
        n_periods = len(payment_schedule)
        entries = self._generate_ifrs16_schedule(
            rou_asset, lease_liability, payment_schedule, period_rate
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
        self, rou_asset: Decimal, lease_liability: Decimal, payment_schedule: List[Dict], period_rate: Decimal
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

        n_periods = len(payment_schedule)
        depreciation_per_period = (rou_asset / Decimal(str(n_periods))).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        )

        for period_num, payment_info in enumerate(payment_schedule, start=1):
            period_date = payment_info["due_date"]
            payment_amount = payment_info["amount"]

            # Interest expense = Beginning liability * discount rate (effective interest method)
            interest_expense = (remaining_liability * period_rate).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )

            # Principal reduction = Payment - Interest
            principal_reduction = payment_amount - interest_expense

            # Ending liability
            ending_liability = remaining_liability - principal_reduction

            # Depreciation (straight-line)
            if period_num == n_periods:
                # Last period: depreciate remaining balance to ensure ROU asset reaches zero
                depreciation = remaining_asset
            else:
                depreciation = depreciation_per_period

            ending_asset = remaining_asset - depreciation

            # Total expense = Interest + Depreciation
            total_expense = interest_expense + depreciation

            entries.append({
                "period": period_num,
                "period_date": period_date,
                "lease_payment": payment_amount,
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
