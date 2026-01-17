"""
Integration tests for lease calculators.

Tests the calculation logic for ASC 842 and IFRS 16 schedules.
Verifies mathematical accuracy and compliance with accounting standards.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from app.services.asc842_calculator import ASC842Calculator
from app.services.ifrs16_calculator import IFRS16Calculator
from app.models.lease import Lease
from app.models.journals import Payments


def _payment_periods(lease: Lease) -> int:
    frequency_map = {
        "monthly": lease.lease_term_months,
        "quarterly": lease.lease_term_months // 3,
        "annual": lease.lease_term_months // 12,
    }
    return frequency_map.get(lease.payment_frequency, lease.lease_term_months)


def _seed_payments(db_session, lease: Lease, count: int | None = None) -> int:
    total_periods = _payment_periods(lease)
    payment_count = min(count or total_periods, total_periods)
    start_date = lease.commencement_date
    step_months = {"monthly": 1, "quarterly": 3, "annual": 12}.get(
        lease.payment_frequency, 1
    )

    for period in range(payment_count):
        due_date = datetime.combine(
            start_date + relativedelta(months=step_months * period),
            datetime.min.time(),
        )
        db_session.add(
            Payments(
                contract_id=str(lease.id),
                amount=lease.periodic_payment,
                due_date=due_date,
                status="Scheduled",
            )
        )
    db_session.commit()
    return payment_count


@pytest.mark.integration
@pytest.mark.calculator
class TestASC842Calculator:
    """Test ASC 842 calculator service"""

    def test_calculate_present_value(self, db_session, sample_lease):
        """Test present value calculation"""
        calculator = ASC842Calculator(sample_lease)
        _seed_payments(db_session, sample_lease)
        payment_schedule = calculator.fetch_payments_from_db(db_session)
        period_rate = calculator.calculate_period_rate_from_payments()
        pv = calculator.calculate_present_value_from_payments(payment_schedule, period_rate)

        assert isinstance(pv, Decimal)
        assert pv > 0
        # PV should be less than total payments
        total_payments = sample_lease.periodic_payment * sample_lease.lease_term_months
        assert pv < total_payments

    def test_calculate_initial_rou_asset(self, db_session, sample_lease):
        """Test initial ROU asset calculation"""
        calculator = ASC842Calculator(sample_lease)
        _seed_payments(db_session, sample_lease)
        payment_schedule = calculator.fetch_payments_from_db(db_session)
        period_rate = calculator.calculate_period_rate_from_payments()
        rou_asset, lease_liability = calculator.calculate_initial_measurements(
            payment_schedule, period_rate
        )

        assert isinstance(rou_asset, Decimal)
        assert rou_asset > 0
        # ROU asset should include initial costs
        assert rou_asset >= lease_liability

    def test_generate_schedule_operating_lease(self, db_session, sample_lease):
        """Test schedule generation for operating lease"""
        calculator = ASC842Calculator(sample_lease)
        payment_count = _seed_payments(db_session, sample_lease)
        schedule = calculator.generate_schedule(db_session)

        assert schedule is not None
        assert schedule.lease_id == sample_lease.id
        assert schedule.initial_rou_asset > 0
        assert schedule.initial_lease_liability > 0
        assert schedule.total_payments > 0

        # Verify schedule entries were created
        assert len(sample_lease.schedule_entries) == payment_count

    def test_generate_schedule_finance_lease(self, db_session, sample_finance_lease):
        """Test schedule generation for finance lease"""
        calculator = ASC842Calculator(sample_finance_lease)
        _seed_payments(db_session, sample_finance_lease)
        schedule = calculator.generate_schedule(db_session)

        assert schedule is not None
        assert schedule.lease_id == sample_finance_lease.id
        # Finance lease should have different calculations
        assert schedule.initial_rou_asset > 0

    def test_schedule_entries_descending_liability(self, db_session, sample_lease):
        """Test that lease liability decreases over time"""
        calculator = ASC842Calculator(sample_lease)
        _seed_payments(db_session, sample_lease)
        calculator.generate_schedule(db_session)

        entries = db_session.query(
            LeaseScheduleEntry
        ).filter_by(
            lease_id=sample_lease.id,
            schedule_type="ASC842"
        ).order_by(LeaseScheduleEntry.period).all()

        # Verify liability decreases each period
        for i in range(len(entries) - 1):
            assert entries[i].lease_liability_ending > entries[i + 1].lease_liability_ending
            # Interest should decrease as liability decreases
            assert entries[i].interest_expense >= entries[i + 1].interest_expense

    def test_schedule_entries_final_period(self, db_session, sample_lease):
        """Test that final period liability is near zero"""
        calculator = ASC842Calculator(sample_lease)
        _seed_payments(db_session, sample_lease)
        calculator.generate_schedule(db_session)

        # Get last entry
        last_entry = db_session.query(
            LeaseScheduleEntry
        ).filter_by(
            lease_id=sample_lease.id,
            schedule_type="ASC842"
        ).order_by(LeaseScheduleEntry.period.desc()).first()

        # Final liability should be very close to zero (within rounding tolerance)
        assert abs(last_entry.lease_liability_ending) < Decimal("1.00")

    def test_total_payments_match(self, db_session, sample_lease):
        """Test that total payments in schedule match expected total"""
        calculator = ASC842Calculator(sample_lease)
        payment_count = _seed_payments(db_session, sample_lease)
        calculator.generate_schedule(db_session)

        entries = db_session.query(
            LeaseScheduleEntry
        ).filter_by(
            lease_id=sample_lease.id,
            schedule_type="ASC842"
        ).all()

        total_payments = sum(entry.lease_payment for entry in entries)
        expected_total = sample_lease.periodic_payment * payment_count

        assert abs(total_payments - expected_total) < Decimal("0.01")

    def test_interest_calculation_accuracy(self, db_session, sample_lease):
        """Test interest calculation accuracy"""
        calculator = ASC842Calculator(sample_lease)
        _seed_payments(db_session, sample_lease)
        calculator.generate_schedule(db_session)

        # Get first entry to verify interest calculation
        first_entry = db_session.query(
            LeaseScheduleEntry
        ).filter_by(
            lease_id=sample_lease.id,
            schedule_type="ASC842",
            period=1
        ).first()

        # Calculate expected monthly interest
        period_rate = calculator.calculate_period_rate_from_payments()
        expected_interest = first_entry.lease_liability_beginning * period_rate

        # Should be very close (within rounding)
        assert abs(first_entry.interest_expense - expected_interest) < Decimal("0.01")


@pytest.mark.integration
@pytest.mark.calculator
class TestIFRS16Calculator:
    """Test IFRS 16 calculator service"""

    def test_calculate_present_value(self, db_session, sample_lease):
        """Test present value calculation for IFRS 16"""
        calculator = IFRS16Calculator(sample_lease)
        pv = calculator.calculate_present_value()

        assert isinstance(pv, Decimal)
        assert pv > 0

    def test_calculate_initial_rou_asset(self, db_session, sample_lease):
        """Test initial ROU asset calculation for IFRS 16"""
        calculator = IFRS16Calculator(sample_lease)
        rou_asset, _ = calculator.calculate_initial_measurements()

        assert isinstance(rou_asset, Decimal)
        assert rou_asset > 0

    def test_generate_schedule(self, db_session, sample_lease):
        """Test IFRS 16 schedule generation"""
        calculator = IFRS16Calculator(sample_lease)
        schedule = calculator.generate_schedule(db_session)

        assert schedule is not None
        assert schedule.lease_id == sample_lease.id
        assert schedule.initial_rou_asset > 0
        assert schedule.initial_lease_liability > 0
        assert schedule.total_payments > 0

        # Verify schedule entries
        entries = db_session.query(
            LeaseScheduleEntry
        ).filter_by(
            lease_id=sample_lease.id,
            schedule_type="IFRS16"
        ).all()

        assert len(entries) == calculator.calculate_payment_periods()

    def test_ifrs16_vs_asc842_comparison(self, db_session, sample_lease):
        """Test differences between IFRS 16 and ASC 842 calculations"""
        # Generate both schedules
        asc842_calc = ASC842Calculator(sample_lease)
        ifrs16_calc = IFRS16Calculator(sample_lease)

        _seed_payments(db_session, sample_lease)
        asc842_schedule = asc842_calc.generate_schedule(db_session)
        db_session.expunge(asc842_schedule)  # Detach to avoid conflicts

        ifrs16_schedule = ifrs16_calc.generate_schedule(db_session)

        # Both should have similar initial values
        # (may differ slightly based on implementation)
        difference = abs(
            asc842_schedule.initial_lease_liability - ifrs16_schedule.initial_lease_liability
        )
        assert difference < (asc842_schedule.total_payments * Decimal("0.10"))


@pytest.mark.integration
@pytest.mark.calculator
class TestCalculatorEdgeCases:
    """Test edge cases and special scenarios"""

    def test_zero_initial_costs(self, db_session):
        """Test calculation with zero initial direct costs"""
        lease = Lease(
            lease_name="Zero Cost Lease",
            lessor_name="Lessor",
            lessee_name="Lessee",
            commencement_date=date(2024, 1, 1),
            lease_term_months=12,
            periodic_payment=Decimal("1000.00"),
            initial_direct_costs=Decimal("0"),
            prepaid_rent=Decimal("0"),
            lease_incentives=Decimal("0"),
            incremental_borrowing_rate=Decimal("0.05"),
            discount_rate=Decimal("0.05")
        )
        db_session.add(lease)
        db_session.commit()

        calculator = ASC842Calculator(lease)
        _seed_payments(db_session, lease)
        schedule = calculator.generate_schedule(db_session)

        assert schedule.initial_rou_asset > 0
        assert schedule.initial_lease_liability > 0

    def test_high_discount_rate(self, db_session):
        """Test calculation with high discount rate"""
        lease = Lease(
            lease_name="High Rate Lease",
            lessor_name="Lessor",
            lessee_name="Lessee",
            commencement_date=date(2024, 1, 1),
            lease_term_months=24,
            periodic_payment=Decimal("5000.00"),
            incremental_borrowing_rate=Decimal("0.15"),  # 15%
            discount_rate=Decimal("0.15")
        )
        db_session.add(lease)
        db_session.commit()

        calculator = ASC842Calculator(lease)
        _seed_payments(db_session, lease)
        payment_schedule = calculator.fetch_payments_from_db(db_session)
        period_rate = calculator.calculate_period_rate_from_payments()
        pv = calculator.calculate_present_value_from_payments(payment_schedule, period_rate)

        # Higher discount rate should result in lower PV
        assert pv < lease.periodic_payment * lease.lease_term_months

    def test_long_term_lease(self, db_session):
        """Test calculation for long-term lease (10 years)"""
        lease = Lease(
            lease_name="Long Term Lease",
            lessor_name="Lessor",
            lessee_name="Lessee",
            commencement_date=date(2024, 1, 1),
            lease_term_months=120,  # 10 years
            periodic_payment=Decimal("10000.00"),
            incremental_borrowing_rate=Decimal("0.06"),
            discount_rate=Decimal("0.06")
        )
        db_session.add(lease)
        db_session.commit()

        calculator = ASC842Calculator(lease)
        _seed_payments(db_session, lease)
        schedule = calculator.generate_schedule(db_session)

        # Verify all 120 periods were created
        entries = db_session.query(
            LeaseScheduleEntry
        ).filter_by(
            lease_id=lease.id,
            schedule_type="ASC842"
        ).all()

        assert len(entries) == 120

    def test_quarterly_payments(self, db_session):
        """Test calculation with quarterly payment frequency"""
        lease = Lease(
            lease_name="Quarterly Lease",
            lessor_name="Lessor",
            lessee_name="Lessee",
            commencement_date=date(2024, 1, 1),
            lease_term_months=36,
            periodic_payment=Decimal("15000.00"),
            payment_frequency="quarterly",
            incremental_borrowing_rate=Decimal("0.05"),
            discount_rate=Decimal("0.05")
        )
        db_session.add(lease)
        db_session.commit()

        calculator = ASC842Calculator(lease)
        _seed_payments(db_session, lease)
        schedule = calculator.generate_schedule(db_session)

        assert schedule is not None
        # Should still generate monthly entries
        entries = db_session.query(
            LeaseScheduleEntry
        ).filter_by(lease_id=lease.id).all()

        assert len(entries) > 0


# Import statement needed for the tests
from app.models.lease import LeaseScheduleEntry
