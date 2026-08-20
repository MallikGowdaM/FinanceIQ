"""
Loan Risk — DRF API Views.
Each view calls services.py for analytics and returns clean JSON.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from . import services
from .models import Loan


class DefaultByCreditBandView(APIView):
    """GET /api/loan-risk/default-by-credit-band/
    Returns default rate per credit score band (Poor/Fair/Good/Very Good/Exceptional).
    """
    def get(self, request):
        data = services.default_rate_by_credit_band()
        return Response(data)


class DefaultByDTIView(APIView):
    """GET /api/loan-risk/default-by-dti/
    Returns default rate per DTI bucket.
    """
    def get(self, request):
        data = services.default_rate_by_dti()
        return Response(data)


class RiskDistributionView(APIView):
    """GET /api/loan-risk/risk-distribution/
    Returns count per risk segment (Low / Medium / High).
    """
    def get(self, request):
        data = services.risk_distribution()
        return Response(data)


class IncomeVsLoanScatterView(APIView):
    """GET /api/loan-risk/scatter/
    Returns list of {income, loan_amount, status, risk_segment} for scatter chart.
    """
    def get(self, request):
        data = services.income_vs_loan_scatter()
        return Response(data)


class RiskDriversView(APIView):
    """GET /api/loan-risk/risk-drivers/
    Returns top features correlated with default (point-biserial correlation).
    """
    def get(self, request):
        data = services.top_risk_drivers()
        return Response(data)


class PredictRiskView(APIView):
    """POST /api/loan-risk/predict/
    Body: {credit_score, dti_ratio, income, loan_amount}
    Returns: {risk_segment: "Low"|"Medium"|"High"}
    """
    def post(self, request):
        try:
            credit_score = float(request.data.get("credit_score", 0))
            dti_ratio = float(request.data.get("dti_ratio", 0))
            income = float(request.data.get("income", 0))
            loan_amount = float(request.data.get("loan_amount", 0))
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid numeric fields"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        segment = services.compute_risk_segment(credit_score, dti_ratio, income, loan_amount)
        return Response({"risk_segment": segment})


class SummaryKPIsView(APIView):
    """GET /api/loan-risk/summary/
    Returns overall KPIs: total loans, default rate, avg credit score, avg dti.
    """
    def get(self, request):
        data = services.summary_kpis()
        return Response(data)
