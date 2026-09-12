import math
from typing import Dict, Any, List


def calculate_financial_structure(margin_capital: float) -> Dict[str, Any]:
    """
    Computes total project cost, loan eligibility, auto-routes scheme,
    and constructs a quarterly repayment schedule with moratorium accounting.
    """
    if margin_capital <= 0:
        raise ValueError("Margin capital must be strictly greater than 0.")

    # 1. 10% Beneficiary Margin -> 100% Project Cost, 90% Concessional Loan
    project_cost = margin_capital / 0.10
    raw_loan_eligibility = project_cost * 0.90

    # 2. Scheme Routing
    if project_cost <= 140000.0:  # <= ₹1.40 Lakh
        scheme_name = "Micro Finance Scheme"
        loan_amount = min(raw_loan_eligibility, 125000.0)  # Max ₹1.25 Lakh
        annual_rate = 0.065  # 6.5% p.a.
        total_tenure_months = 36  # 3 Years
        moratorium_months = 3
    elif project_cost <= 5000000.0:  # > ₹1.40 Lakh and <= ₹50.00 Lakh
        scheme_name = "Term Loan Scheme"
        loan_amount = min(raw_loan_eligibility, 4500000.0)  # Max ₹45 Lakh
        annual_rate = 0.08  # 8.0% p.a.
        total_tenure_months = 84  # 7 Years
        moratorium_months = 6
    else:
        raise ValueError("Project cost exceeds the ₹50.00 Lakh maximum ceiling under concessional schemes.")

    # 3. Quarterly Repayment Calculations
    quarterly_rate = annual_rate / 4
    moratorium_quarters = moratorium_months // 3
    total_quarters = total_tenure_months // 3
    repayment_quarters = total_quarters - moratorium_quarters

    # EMI Formula: E = P * [r(1+r)^n] / [(1+r)^n - 1]
    emi_quarterly = loan_amount * (
        (quarterly_rate * math.pow(1 + quarterly_rate, repayment_quarters))
        / (math.pow(1 + quarterly_rate, repayment_quarters) - 1)
    )

    # 4. Amortization Schedule
    schedule: List[Dict[str, Any]] = []
    balance = loan_amount

    # Moratorium Phase (Interest serviced quarterly, principal intact)
    for q in range(1, moratorium_quarters + 1):
        interest_charge = balance * quarterly_rate
        schedule.append({
            "quarter": q,
            "phase": "Moratorium",
            "principal_repayment": 0.0,
            "interest_payment": round(interest_charge, 2),
            "total_installment": round(interest_charge, 2),
            "remaining_balance": round(balance, 2)
        })

    # Repayment Phase
    for q in range(moratorium_quarters + 1, total_quarters + 1):
        interest_charge = balance * quarterly_rate
        principal_payment = emi_quarterly - interest_charge
        balance -= principal_payment
        if balance < 0 or q == total_quarters:
            balance = 0.0

        schedule.append({
            "quarter": q,
            "phase": "Repayment",
            "principal_repayment": round(principal_payment, 2),
            "interest_payment": round(interest_charge, 2),
            "total_installment": round(emi_quarterly, 2),
            "remaining_balance": round(balance, 2)
        })

    total_payable = sum(item["total_installment"] for item in schedule)

    return {
        "user_margin_capital": round(margin_capital, 2),
        "total_project_cost": round(project_cost, 2),
        "sanctioned_loan_amount": round(loan_amount, 2),
        "scheme_details": {
            "name": scheme_name,
            "interest_rate_percent": round(annual_rate * 100, 2),
            "tenure_years": total_tenure_months // 12,
            "moratorium_period_months": moratorium_months
        },
        "quarterly_emi": round(emi_quarterly, 2),
        "total_interest_payable": round(total_payable - loan_amount, 2),
        "total_amount_payable": round(total_payable, 2),
        "amortization_schedule": schedule
    }