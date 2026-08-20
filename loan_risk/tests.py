"""
Loan Risk — Unit Tests

Tests focus on the service layer (business logic), not the HTTP layer.
These are the calculations that matter for a portfolio demo — they verify
that the risk scoring and analytics functions produce correct outputs.
"""
from decimal import Decimal
from datetime import date

from django.test import TestCase, Client
from django.urls import reverse

from .models import Borrower, Loan
from .services import (
    compute_risk_segment,
    default_rate_by_credit_band,
    default_rate_by_dti,
    risk_distribution,
    income_vs_loan_scatter,
    top_risk_drivers,
    summary_kpis,
)


class RiskSegmentTests(TestCase):
    """Test compute_risk_segment() — the core risk scoring function."""

    def test_low_risk_high_credit_low_dti(self):
        """High credit score + low DTI + small loan → Low risk."""
        segment = compute_risk_segment(
            credit_score=780,
            dti_ratio=12.0,
            income=80000,
            loan_amount=10000,
        )
        self.assertEqual(segment, "Low")

    def test_high_risk_low_credit_high_dti(self):
        """Low credit score + high DTI → High risk."""
        segment = compute_risk_segment(
            credit_score=520,
            dti_ratio=45.0,
            income=30000,
            loan_amount=50000,
        )
        self.assertEqual(segment, "High")

    def test_medium_risk_borderline(self):
        """Mid-range credit + moderate DTI → Medium risk."""
        segment = compute_risk_segment(
            credit_score=630,
            dti_ratio=28.0,
            income=50000,
            loan_amount=20000,
        )
        self.assertEqual(segment, "Medium")

    def test_high_lti_raises_risk(self):
        """Very high loan-to-income ratio should push risk up."""
        # Good credit but loan is 6x income → high LTI adds +2
        segment = compute_risk_segment(
            credit_score=700,
            dti_ratio=25.0,
            income=20000,
            loan_amount=130000,  # 6.5x income
        )
        # Should be Medium or High — not Low
        self.assertIn(segment, ["Medium", "High"])

    def test_exceptional_credit_always_low(self):
        """Exceptional credit (820) with normal DTI → Low risk."""
        segment = compute_risk_segment(
            credit_score=820,
            dti_ratio=15.0,
            income=100000,
            loan_amount=15000,
        )
        self.assertEqual(segment, "Low")

    def test_zero_income_does_not_crash(self):
        """income=0 must not cause ZeroDivisionError."""
        segment = compute_risk_segment(
            credit_score=650,
            dti_ratio=30.0,
            income=0,
            loan_amount=10000,
        )
        # Any valid segment is acceptable — just must not raise
        self.assertIn(segment, ["Low", "Medium", "High"])


class ServiceAggregationTests(TestCase):
    """Test analytics aggregation functions with seeded test data."""

    @classmethod
    def setUpTestData(cls):
        """Create a small but representative dataset for tests."""
        # Create 3 borrowers with different risk profiles
        cls.b_low = Borrower.objects.create(
            age=35, income=80000, employment_length=10,
            credit_score=760, dti_ratio=12.0, home_ownership="OWN"
        )
        cls.b_med = Borrower.objects.create(
            age=28, income=45000, employment_length=3,
            credit_score=640, dti_ratio=28.0, home_ownership="RENT"
        )
        cls.b_high = Borrower.objects.create(
            age=22, income=25000, employment_length=1,
            credit_score=510, dti_ratio=48.0, home_ownership="RENT"
        )

        # Create loans
        Loan.objects.create(
            borrower=cls.b_low, loan_amount=10000, interest_rate=6.5,
            purpose="car", issue_date=date(2023, 1, 1),
            status="paid", risk_segment="Low"
        )
        Loan.objects.create(
            borrower=cls.b_med, loan_amount=20000, interest_rate=12.0,
            purpose="debt_consolidation", issue_date=date(2023, 3, 1),
            status="current", risk_segment="Medium"
        )
        Loan.objects.create(
            borrower=cls.b_high, loan_amount=8000, interest_rate=22.0,
            purpose="medical", issue_date=date(2023, 6, 1),
            status="default", risk_segment="High"
        )

    def test_default_rate_by_credit_band_returns_list(self):
        """Should return a list of dicts with required keys."""
        result = default_rate_by_credit_band()
        self.assertIsInstance(result, list)
        if result:
            row = result[0]
            self.assertIn("band", row)
            self.assertIn("default_rate", row)
            self.assertIn("total", row)

    def test_default_rate_by_dti_returns_list(self):
        result = default_rate_by_dti()
        self.assertIsInstance(result, list)

    def test_risk_distribution_counts_correct(self):
        """Risk distribution should return Low=1, Medium=1, High=1."""
        result = risk_distribution()
        dist = {r["segment"]: r["count"] for r in result}
        self.assertEqual(dist.get("Low"), 1)
        self.assertEqual(dist.get("Medium"), 1)
        self.assertEqual(dist.get("High"), 1)

    def test_scatter_returns_income_and_loan(self):
        result = income_vs_loan_scatter()
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn("income", result[0])
        self.assertIn("loan_amount", result[0])

    def test_summary_kpis_default_rate(self):
        """With 1 default out of 3 loans, default rate should be ~33.3%."""
        kpis = summary_kpis()
        self.assertAlmostEqual(kpis["default_rate"], 33.3, delta=1.0)
        self.assertEqual(kpis["total_loans"], 3)


class LoanRiskAPITests(TestCase):
    """Test DRF API endpoints return 200 and valid JSON."""

    def setUp(self):
        self.client = Client()

    def test_default_by_credit_band_endpoint(self):
        resp = self.client.get("/api/loan-risk/default-by-credit-band/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_risk_distribution_endpoint(self):
        resp = self.client.get("/api/loan-risk/risk-distribution/")
        self.assertEqual(resp.status_code, 200)

    def test_predict_endpoint_returns_segment(self):
        import json
        resp = self.client.post(
            "/api/loan-risk/predict/",
            data=json.dumps({"credit_score": 750, "dti_ratio": 15, "income": 80000, "loan_amount": 10000}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("risk_segment", data)
        self.assertIn(data["risk_segment"], ["Low", "Medium", "High"])

    def test_summary_endpoint(self):
        resp = self.client.get("/api/loan-risk/summary/")
        self.assertEqual(resp.status_code, 200)
