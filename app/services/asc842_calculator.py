from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Tuple
import logging
import numpy as np
from sqlalchemy.orm import Session

from app.models.lease import Lease, LeaseScheduleEntry, LeaseClassification
from app.models.schedule import ASC842Schedule
from app.models.journals import Payments
from .utils import make_json_safe

logger = logging.getLogger(__name__)


class ASC842Calculator:
    """
    ASC 842 Lease Accounting Calculator using Database Payment Records
    
    This calculator fetches actual payment data from the Payments table
    and generates lease accounting schedules based on those payments.
    
    Uses beginning-of-period payment timing with proper accrual accounting.
    """

    def __init__(self, lease: Lease):
        self.lease = lease
        logger.debug("Initialized ASC842Calculator for lease %s", self.lease)

    def fetch_payments_from_db(self, db: Session) -> List[Dict]:
        """
        Fetch payments from database for this lease
        Returns list of payment dictionaries with amount and due_date
        """
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
        
        logger.debug("Payment schedule loaded for lease %s: %s", self.lease.id, payment_schedule)
        return payment_schedule

    # def calculate_period_rate_from_payments(self, payment_schedule: List[Dict]) -> Decimal:
    #     """
    #     Calculate periodic interest rate based on payment frequency
    #     Determines frequency from payment schedule dates
    #     """
    #     if len(payment_schedule) < 2:
    #         # Default to monthly if only one payment
    #         return self.lease.incremental_borrowing_rate / Decimal("12")
        
    #     # Calculate average days between payments
    #     days_between = []
    #     for i in range(len(payment_schedule) - 1):
    #         date1 = payment_schedule[i]["due_date"]
    #         date2 = payment_schedule[i + 1]["due_date"]
    #         days = (date2 - date1).days
    #         days_between.append(days)
        
    #     avg_days = sum(days_between) / len(days_between)
        
    #     # Determine payment frequency
    #     if avg_days <= 35:  # ~Monthly
    #         periods_per_year = Decimal("12")
    #     elif avg_days <= 100:  # ~Quarterly
    #         periods_per_year = Decimal("4")
    #     else:  # ~Annual
    #         periods_per_year = Decimal("1")
        
    #     return self.lease.incremental_borrowing_rate / periods_per_year
    
    def calculate_period_rate_from_payments(self, payment_schedule: List[Dict]) -> Decimal:
        """Calculate periodic interest rate from annual IBR and payment cadence"""
        annual_rate = self.lease.incremental_borrowing_rate / 100
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
        logger.debug("Calculated period_rate for lease %s: %s", self.lease.id, annual_rate / periods)
        return annual_rate / periods

    def calculate_present_value_from_payments(
        self, payment_schedule: List[Dict], period_rate: Decimal
    ) -> Decimal:
        """
        Calculate present value of lease payments
        Uses beginning-of-period timing (annuity due)
        
        For annuity due (payment at beginning of period):
        PV = PMT + PMT × [(1 - (1 + r)^-(n-1)) / r]
        
        Or for individual payments:
        PV = Sum of [Payment_i / (1 + r)^(i-1)] for i = 1 to n
        """
        pv = Decimal("0")
        rate = float(period_rate)
        
        # Calculate PV for each payment (beginning of period)
        for period_num, payment in enumerate(payment_schedule, start=1):
            payment_amount = float(payment["amount"])
            
            if rate == 0:
                discount_factor = 1.0
            else:
                # Beginning of period: discount by (period - 1)
                # Period 1 payment has no discount, period 2 discounted by 1 period, etc.
                discount_factor = 1.0 / ((1.0 + rate) ** period_num)
            
            payment_pv = Decimal(str(payment_amount * discount_factor))
            pv += payment_pv
        
        # Add present value of residual value if applicable
        if self.lease.residual_value > 0:
            n_periods = len(payment_schedule)
            if rate > 0:
                residual_pv = float(self.lease.residual_value) / ((1.0 + rate) ** n_periods)
                pv += Decimal(str(residual_pv))
            else:
                pv += self.lease.residual_value
        
        return pv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_initial_measurements(
        self, payment_schedule: List[Dict], period_rate: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate initial ROU asset and lease liability
        
        Lease Liability = PV of lease payments
        ROU Asset = Lease Liability + Initial Direct Costs + Prepaid Rent - Lease Incentives
        """
        lease_liability = self.calculate_present_value_from_payments(
            payment_schedule, period_rate
        )
        
        rou_asset = (
            lease_liability
            + self.lease.initial_direct_costs
            + self.lease.prepaid_rent
            - self.lease.lease_incentives
        )
        logger.debug("Initial measurements for lease %s: liability=%s, rou_asset=%s", self.lease.id, lease_liability, rou_asset)
        return rou_asset, lease_liability

    def generate_schedule(self, db: Session) -> ASC842Schedule:
        """Generate complete ASC 842 lease schedule from database payments"""
        
        # Fetch payments from database
        payment_schedule = self.fetch_payments_from_db(db)
        logger.debug("Fetched payment schedule for lease %s", self.lease.id)
        
        # Calculate period rate based on payment frequency
        period_rate = self.calculate_period_rate_from_payments(payment_schedule)
        logger.debug("Period rate for lease %s: %s", self.lease.id, period_rate)
        
        # Calculate initial measurements
        rou_asset, lease_liability = self.calculate_initial_measurements(
            payment_schedule, period_rate
        )
        logger.debug("ROU asset and liability for lease %s: %s, %s", self.lease.id, rou_asset, lease_liability)
        
        # Generate schedule entries based on lease classification
        if self.lease.classification == LeaseClassification.FINANCE:
            entries = self._generate_finance_lease_schedule(
                rou_asset, lease_liability, payment_schedule, period_rate
            )
        else:
            entries = self._generate_operating_lease_schedule(
                rou_asset, lease_liability, payment_schedule, period_rate
            )
        
        # Calculate totals from entries (skip period 0)
        actual_entries = [e for e in entries if e["period"] > 0]
        total_payments = sum(e["lease_payment"] for e in actual_entries)
        total_interest = sum(e["interest_expense"] for e in actual_entries)
        total_amortization = sum(e["amortization"] for e in actual_entries)
        
        # Safe JSON Serializer
        entries = make_json_safe(entries)

        # Create schedule record
        schedule = ASC842Schedule(
            lease_id=self.lease.id,
            initial_rou_asset=rou_asset,
            initial_lease_liability=lease_liability,
            total_payments=total_payments,
            total_interest=total_interest,
            total_amortization=total_amortization,
            schedule_data={"entries": entries, "payment_count": len(payment_schedule)},
        )
        db.add(schedule)
        
        # Create schedule entries (skip period 0 for database storage)
        for entry_data in entries:
            if entry_data["period"] > 0:  # Only store actual payment periods
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
        self, rou_asset: Decimal, lease_liability: Decimal, 
        payment_schedule: List[Dict], period_rate: Decimal
    ) -> List[Dict]:
        """
        Generate schedule for finance lease with beginning-of-period payments
        
        Period 0: Initial measurement
        Period 1+: Payment at beginning, then accrue interest
        
        Flow for each period:
        1. Record beginning balances
        2. Make payment (reduces liability)
        3. Accrue interest on remaining liability
        4. Record amortization
        5. Calculate ending balances
        """
        entries = []
        n_periods = len(payment_schedule)
        
        # Straight-line amortization
        amortization_per_period = (rou_asset / Decimal(str(n_periods))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Period 0: Initial measurement (commencement date)
        entries.append({
            "period": 0,
            "period_date": self.lease.commencement_date,
            "lease_payment": Decimal("0"),
            "interest_expense": Decimal("0"),
            "principal_reduction": Decimal("0"),
            "lease_liability_beginning": lease_liability,
            "lease_liability_ending": lease_liability,
            "rou_asset_beginning": rou_asset,
            "amortization": Decimal("0"),
            "rou_asset_ending": rou_asset,
            "total_expense": Decimal("0"),
        })
        
        # Track running balances
        liability_balance = lease_liability
        asset_balance = rou_asset
        
        for period_num, payment_info in enumerate(payment_schedule, start=1):
            payment_amount = payment_info["amount"]
            period_date = payment_info["due_date"]
            
            # Beginning balances (before payment)
            liability_beginning = liability_balance
            asset_beginning = asset_balance
            
            # Step 1: Make payment (reduces liability - principal reduction)
            principal_reduction = payment_amount
            liability_after_payment = liability_beginning - principal_reduction
            
            # Step 2: Accrue interest on remaining liability
            interest_expense = (liability_after_payment * period_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            # Step 3: Add accrued interest back to liability
            liability_ending = liability_after_payment + interest_expense
            
            # Step 4: Calculate amortization
            if period_num == n_periods:
                amortization = asset_balance  # Last period - amortize remaining
            else:
                amortization = amortization_per_period
            
            asset_ending = asset_balance - amortization
            
            # Total expense = Interest + Amortization
            total_expense = interest_expense + amortization
            
            entries.append({
                "period": period_num,
                "period_date": period_date,
                "lease_payment": payment_amount,
                "interest_expense": interest_expense,
                "principal_reduction": principal_reduction,
                "lease_liability_beginning": liability_beginning,
                "lease_liability_ending": max(liability_ending, Decimal("0")),
                "rou_asset_beginning": asset_beginning,
                "amortization": amortization,
                "rou_asset_ending": max(asset_ending, Decimal("0")),
                "total_expense": total_expense,
            })
            
            # Update balances for next period
            liability_balance = max(liability_ending, Decimal("0"))
            asset_balance = max(asset_ending, Decimal("0"))
        
        return entries

    def _generate_operating_lease_schedule(
        self, rou_asset: Decimal, lease_liability: Decimal,
        payment_schedule: List[Dict], period_rate: Decimal
    ) -> List[Dict]:
        """
        Generate schedule for operating lease with beginning-of-period payments
        
        Operating lease: Straight-line expense recognition
        
        Flow:
        1. Calculate straight-line expense
        2. For each period:
           - Make payment
           - Accrue interest
           - Calculate amortization as plug (Straight-line - Interest)
        """
        entries = []
        n_periods = len(payment_schedule)
        
        # Calculate straight-line expense
        total_payments = sum(p["amount"] for p in payment_schedule)
        total_lease_cost = total_payments + self.lease.initial_direct_costs
        straight_line_expense = (total_lease_cost / Decimal(str(n_periods))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        logger.debug(
            "Operating lease totals for lease %s: payments=%s, total_lease_cost=%s, straight_line_expense=%s",
            self.lease.id,
            total_payments,
            total_lease_cost,
            straight_line_expense,
        )
        
        # Period 0: Initial measurement
        entries.append({
            "period": 0,
            "period_date": self.lease.commencement_date,
            "lease_payment": Decimal("0"),
            "interest_expense": Decimal("0"),
            "principal_reduction": Decimal("0"),
            "lease_liability_beginning": lease_liability,
            "lease_liability_ending": lease_liability,
            "rou_asset_beginning": rou_asset,
            "amortization": Decimal("0"),
            "rou_asset_ending": rou_asset,
            "total_expense": Decimal("0"),
        })
        
        # Track running balances
        liability_balance = lease_liability
        asset_balance = rou_asset
        
        for period_num, payment_info in enumerate(payment_schedule, start=1):
            payment_amount = payment_info["amount"]
            period_date = payment_info["due_date"]
            
            # Beginning balances
            liability_beginning = liability_balance
            asset_beginning = asset_balance
            
            # interest_expense = (liability_beginning * period_rate).quantize(
            #     Decimal("0.01"), rounding=ROUND_HALF_UP
            # )

            # Step 1: Make payment (principal reduction)
            principal_reduction = payment_amount
            liability_after_payment = liability_beginning - principal_reduction
            
            # Step 2: Accrue interest on remaining liability
            interest_expense = (liability_beginning * period_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            # Step 3: Add accrued interest to liability
            liability_ending = liability_after_payment + interest_expense
            
            # Step 4: Amortization is plug to achieve straight-line expense
            amortization = straight_line_expense - interest_expense
            
            # Safety check
            if amortization < 0:
                amortization = Decimal("0")
            if amortization > asset_balance:
                amortization = asset_balance
            
            asset_ending = asset_balance - amortization
            
            entry = {
                "period": period_num,
                "period_date": period_date,
                "lease_payment": payment_amount,
                "interest_expense": interest_expense,
                "principal_reduction": principal_reduction,
                "lease_liability_beginning": liability_beginning,
                "lease_liability_ending": max(liability_ending, Decimal("0")),
                "rou_asset_beginning": asset_beginning,
                "amortization": amortization,
                "rou_asset_ending": max(asset_ending, Decimal("0")),
                "total_expense": straight_line_expense,
            }
            entries.append(entry)
            logger.debug(
                "Operating lease period %s for lease %s: %s",
                period_num,
                self.lease.id,
                entry,
            )
            # Update balances
            liability_balance = max(liability_ending, Decimal("0"))
            asset_balance = max(asset_ending, Decimal("0"))
        
        return entries
