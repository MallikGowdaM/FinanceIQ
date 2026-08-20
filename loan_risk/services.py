"""
Loan Risk — Service Layer

All analytics / pandas logic lives here. Views stay thin.
Separation keeps testability clean and views readable.
"""
import numpy as np
import pandas as pd
from django.db.models import Avg, Count

from .models import Borrower, Loan



# ─── Risk Scoring ────────────────────────────────────────────────────────────

def compute_risk_segment(
    credit_score: float,
    dti_ratio: float,
    income: float,
    loan_amount: float = 0,
) -> str:
    """
    Compute a risk segment (Low / Medium / High) from borrower attributes.

    Scoring logic (points-based, simple rules that approximate real underwriting):
    - Credit score < 580 → +3 High risk points
    - Credit score 580–669 → +2 Medium risk points
    - Credit score 670–739 → +1 Low-ish risk
    - DTI > 40% → +3
    - DTI 30–40% → +2
    - DTI 20–30% → +1
    - Loan-to-income > 5x → +2
    - Loan-to-income > 2.5x → +1

    Total ≥ 5 → High; 3–4 → Medium; ≤ 2 → Low
    """
    score = 0

    # Credit score component
    if credit_score < 580:
        score += 3
    elif credit_score < 670:
        score += 2
    elif credit_score < 740:
        score += 1

    # DTI component
    if dti_ratio > 40:
        score += 3
    elif dti_ratio > 30:
        score += 2
    elif dti_ratio > 20:
        score += 1

    # Loan-to-income ratio component
    if income > 0 and loan_amount > 0:
        lti = loan_amount / income
        if lti > 5:
            score += 2
        elif lti > 2.5:
            score += 1

    if score >= 5:
        return "High"
    elif score >= 3:
        return "Medium"
    return "Low"


# ─── Aggregation Analytics ───────────────────────────────────────────────────

def _loan_dataframe() -> pd.DataFrame:
    """
    Load all loans + borrower attributes into a flat pandas DataFrame.
    This is the single source for all EDA aggregations — fetch once per request.
    """
    qs = Loan.objects.select_related("borrower").values(
        "id",
        "loan_amount",
        "interest_rate",
        "purpose",
        "status",
        "risk_segment",
        "borrower__credit_score",
        "borrower__dti_ratio",
        "borrower__income",
        "borrower__age",
        "borrower__employment_length",
        "borrower__home_ownership",
    )
    df = pd.DataFrame(list(qs))
    if df.empty:
        return df

    # Rename columns for readability
    df = df.rename(
        columns={
            "borrower__credit_score": "credit_score",
            "borrower__dti_ratio": "dti_ratio",
            "borrower__income": "income",
            "borrower__age": "age",
            "borrower__employment_length": "employment_length",
            "borrower__home_ownership": "home_ownership",
        }
    )
    # Binary default flag — needed for correlation calculations
    df["is_default"] = (df["status"] == "default").astype(int)
    df["credit_score"] = df["credit_score"].astype(float)
    df["dti_ratio"] = df["dti_ratio"].astype(float)
    df["income"] = df["income"].astype(float)
    df["loan_amount"] = df["loan_amount"].astype(float)
    return df


def default_rate_by_credit_band() -> list[dict]:
    """
    Group loans by FICO credit score band and return default rate per band.
    Bands follow standard FICO tiers:
      Poor <580 | Fair 580-669 | Good 670-739 | Very Good 740-799 | Exceptional 800+
    """
    df = _loan_dataframe()
    if df.empty:
        return []

    bins = [0, 579, 669, 739, 799, 900]
    labels = ["Poor (<580)", "Fair (580–669)", "Good (670–739)", "Very Good (740–799)", "Exceptional (800+)"]
    df["credit_band"] = pd.cut(df["credit_score"], bins=bins, labels=labels)

    grouped = (
        df.groupby("credit_band", observed=True)
        .agg(total=("id", "count"), defaults=("is_default", "sum"))
        .reset_index()
    )
    grouped["default_rate"] = (grouped["defaults"] / grouped["total"].clip(lower=1) * 100).round(1)

    return [
        {
            "band": row["credit_band"],
            "total": int(row["total"]),
            "defaults": int(row["defaults"]),
            "default_rate": float(row["default_rate"]),
        }
        for _, row in grouped.iterrows()
    ]


def default_rate_by_dti() -> list[dict]:
    """
    Group loans by DTI ratio buckets and return default rate per bucket.
    Buckets: <10%, 10-20%, 20-30%, 30-40%, >40%
    """
    df = _loan_dataframe()
    if df.empty:
        return []

    bins = [0, 10, 20, 30, 40, 200]
    labels = ["<10%", "10–20%", "20–30%", "30–40%", ">40%"]
    df["dti_bucket"] = pd.cut(df["dti_ratio"], bins=bins, labels=labels)

    grouped = (
        df.groupby("dti_bucket", observed=True)
        .agg(total=("id", "count"), defaults=("is_default", "sum"))
        .reset_index()
    )
    grouped["default_rate"] = (grouped["defaults"] / grouped["total"].clip(lower=1) * 100).round(1)

    return [
        {
            "dti_bucket": row["dti_bucket"],
            "total": int(row["total"]),
            "default_rate": float(row["default_rate"]),
        }
        for _, row in grouped.iterrows()
    ]


def risk_distribution() -> list[dict]:
    """Return count of loans per risk segment (Low / Medium / High)."""
    qs = (
        Loan.objects.values("risk_segment")
        .annotate(count=Count("id"))
        .order_by("risk_segment")
    )
    return [{"segment": row["risk_segment"], "count": row["count"]} for row in qs]


def income_vs_loan_scatter() -> list[dict]:
    """
    Return a sample of loans for income vs loan_amount scatter chart.
    Colour-coded by default status. Capped at 500 points for chart performance.
    """
    df = _loan_dataframe()
    if df.empty:
        return []

    # Sample for chart readability
    sample = df.sample(min(500, len(df)), random_state=42)
    return [
        {
            "income": float(row["income"]),
            "loan_amount": float(row["loan_amount"]),
            "status": row["status"],
            "risk_segment": row["risk_segment"],
            "credit_score": int(row["credit_score"]),
        }
        for _, row in sample.iterrows()
    ]


def top_risk_drivers() -> list[dict]:
    """
    Compute point-biserial correlation between continuous features and default status.
    Point-biserial correlation is the appropriate measure when one variable is binary
    (defaulted vs not) and the other is continuous (credit_score, dti_ratio, etc.).
    Returns top features sorted by absolute correlation descending.
    """
    df = _loan_dataframe()
    if df.empty or df["is_default"].nunique() < 2:
        return []

    features = {
        "Credit Score": "credit_score",
        "DTI Ratio": "dti_ratio",
        "Annual Income": "income",
        "Loan Amount": "loan_amount",
        "Age": "age",
        "Employment Length": "employment_length",
    }

    results = []
    for label, col in features.items():
        if col not in df.columns:
            continue
        clean = df[[col, "is_default"]].dropna()
        if len(clean) < 10:
            continue
        # Pearson correlation on binary vs continuous is mathematically identical to Point-Biserial
        corr = clean["is_default"].corr(clean[col])
        if pd.isna(corr):
            corr = 0.0
        results.append(
            {
                "feature": label,
                "correlation": round(float(corr), 3),
                "abs_correlation": abs(round(float(corr), 3)),
                "p_value": 0.0,
            }
        )

    results.sort(key=lambda x: x["abs_correlation"], reverse=True)
    return results


def summary_kpis() -> dict:
    """Return overall KPI metrics for the loan risk dashboard summary panel."""
    df = _loan_dataframe()
    if df.empty:
        return {}

    total = len(df)
    defaults = int(df["is_default"].sum())
    return {
        "total_loans": total,
        "total_borrowers": Borrower.objects.count(),
        "default_rate": round(defaults / max(total, 1) * 100, 1),
        "avg_credit_score": round(float(df["credit_score"].mean()), 0),
        "avg_dti": round(float(df["dti_ratio"].mean()), 1),
        "avg_income": round(float(df["income"].mean()), 0),
        "avg_loan_amount": round(float(df["loan_amount"].mean()), 0),
    }
