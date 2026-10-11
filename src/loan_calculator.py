"""
Loan Calculator Module
----------------------
Implements deterministic financial underwriting mathematics:
1. Fixed Obligation to Income Ratio (FOIR) capacity.
2. Age-adjusted maximum allowable tenure (retirement ceiling).
3. Present value annuity capitalization (Loan sizing by FOIR).
4. Gross salary multiplier sizing.
5. Reducing balance Equated Monthly Installment (EMI) calculations.
"""

from typing import Dict, Any


def calculate_max_allowed_emi(
    monthly_net_income: float,
    max_foir: float,
    existing_monthly_emis: float
) -> float:
    """
    Calculate the net monthly EMI capacity an applicant can service
    without exceeding the lender's FOIR (Fixed Obligation to Income Ratio).

    Formula:
        Max Allowed EMI = (Monthly Net Income * Lender FOIR) - Existing EMIs

    Args:
        monthly_net_income: Verified monthly net salary in INR.
        max_foir: Lender's maximum debt obligation ceiling (e.g., 0.50 for 50%).
        existing_monthly_emis: Sum of currently active EMIs in INR.

    Returns:
        Surplus monthly EMI capacity in INR. If existing obligations exceed
        or meet the ceiling, returns 0.0.
    """
    total_obligation_ceiling = monthly_net_income * max_foir
    available_emi = total_obligation_ceiling - existing_monthly_emis
    return max(0.0, round(available_emi, 2))


def calculate_effective_max_tenure(
    applicant_age: int,
    lender_max_age: int,
    lender_max_tenure_months: int
) -> int:
    """
    Determine the maximum allowable loan tenure in months by factoring in the
    borrower's age at application and the lender's retirement/maturity ceiling.

    Standard Indian lending policy mandates that personal loans must fully mature
    prior to the borrower reaching age 58 (PSBs) or 60 (Private Banks).

    Args:
        applicant_age: Current chronological age in years.
        lender_max_age: Maximum permissible age at loan maturity.
        lender_max_tenure_months: Maximum tenure offered by lender policy.

    Returns:
        Effective maximum tenure in months. Returns 0 if applicant has already
        reached or exceeded the maximum age.
    """
    if applicant_age >= lender_max_age:
        return 0
    months_until_retirement = (lender_max_age - applicant_age) * 12
    return min(lender_max_tenure_months, months_until_retirement)


def calculate_max_loan_by_foir(
    max_allowed_emi: float,
    annual_interest_rate: float,
    tenure_months: int
) -> float:
    """
    Calculate the maximum loan amount supportable by available EMI capacity
    using the Present Value of an Annuity formula.

    Formula:
        r = annual_interest_rate / (12 * 100)
        Max Loan = EMI * [(1 - (1 + r)^(-n)) / r]

    Args:
        max_allowed_emi: Available surplus monthly repayment capacity.
        annual_interest_rate: Nominal annual interest rate in percent (e.g. 11.5).
        tenure_months: Repayment duration in months (n).

    Returns:
        Maximum principal supportable by debt-service capacity in INR.
    """
    if max_allowed_emi <= 0 or tenure_months <= 0:
        return 0.0

    monthly_rate = (annual_interest_rate / 100.0) / 12.0

    if monthly_rate == 0.0:
        return max_allowed_emi * tenure_months

    # Present Value of Ordinary Annuity
    pv_factor = (1.0 - (1.0 + monthly_rate) ** (-tenure_months)) / monthly_rate
    max_principal = max_allowed_emi * pv_factor
    return round(max_principal, 2)


def calculate_max_loan_by_multiplier(
    monthly_net_income: float,
    max_salary_multiplier: float
) -> float:
    """
    Calculate the maximum loan amount restricted by policy salary multiplier.

    Formula:
        Max Loan = Monthly Net Income * Salary Multiplier (e.g., 18x to 24x)

    Args:
        monthly_net_income: Monthly net salary in INR.
        max_salary_multiplier: Maximum income multiplier permitted by lender.

    Returns:
        Maximum principal permitted by salary multiplier cap in INR.
    """
    return round(monthly_net_income * max_salary_multiplier, 2)


def calculate_sanction_amount(
    max_loan_foir: float,
    max_loan_multiplier: float,
    lender_max_loan: float,
    lender_min_loan: float,
    desired_loan_amount: float = None
) -> float:
    """
    Determine the final eligible sanction amount by taking the conservative
    minimum of FOIR capacity, multiplier cap, lender product cap, and
    applicant request, rounded down to standard Indian banking increments (₹1,000).

    Args:
        max_loan_foir: Maximum loan supported by EMI capacity.
        max_loan_multiplier: Maximum loan supported by salary multiplier.
        lender_max_loan: Lender's absolute maximum product cap.
        lender_min_loan: Lender's absolute minimum loan ticket size.
        desired_loan_amount: Optional applicant requested amount.

    Returns:
        Eligible sanction principal in INR. Returns 0.0 if the calculated
        amount falls below the lender's minimum ticket size.
    """
    theoretical_max = min(max_loan_foir, max_loan_multiplier, lender_max_loan)

    if desired_loan_amount is not None and desired_loan_amount > 0:
        candidate_amount = min(theoretical_max, desired_loan_amount)
    else:
        candidate_amount = theoretical_max

    # Round down to nearest 1,000 INR
    sanction_amount = float(int(candidate_amount // 1000) * 1000)

    if sanction_amount < lender_min_loan:
        return 0.0

    return sanction_amount


def calculate_monthly_emi(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int
) -> float:
    """
    Calculate the Equated Monthly Installment (EMI) on a reducing balance basis.

    Formula:
        EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)

    Args:
        principal: Loan principal amount in INR.
        annual_interest_rate: Nominal annual interest rate in percent.
        tenure_months: Repayment duration in months.

    Returns:
        Monthly EMI in INR.
    """
    if principal <= 0 or tenure_months <= 0:
        return 0.0

    monthly_rate = (annual_interest_rate / 100.0) / 12.0

    if monthly_rate == 0.0:
        return round(principal / tenure_months, 2)

    compounded = (1.0 + monthly_rate) ** tenure_months
    emi = principal * monthly_rate * compounded / (compounded - 1.0)
    return round(emi, 2)


def calculate_loan_schedule_summary(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int,
    processing_fee_percent: float = 0.0
) -> Dict[str, Any]:
    """
    Generate an underwriting repayment summary including EMI, total interest,
    total repayment outflow, and upfront processing fees.

    Args:
        principal: Approved loan amount in INR.
        annual_interest_rate: Applicable interest rate in percent.
        tenure_months: Loan duration in months.
        processing_fee_percent: Upfront administrative processing fee percentage.

    Returns:
        Dictionary containing comprehensive loan financial metrics.
    """
    emi = calculate_monthly_emi(principal, annual_interest_rate, tenure_months)
    total_repayment = round(emi * tenure_months, 2)
    total_interest = round(max(0.0, total_repayment - principal), 2)
    processing_fee_inr = round(principal * (processing_fee_percent / 100.0), 2)

    return {
        "sanction_amount": principal,
        "tenure_months": tenure_months,
        "interest_rate_pct": annual_interest_rate,
        "monthly_emi": emi,
        "total_interest": total_interest,
        "total_repayment": total_repayment,
        "processing_fee_pct": processing_fee_percent,
        "processing_fee_inr": processing_fee_inr,
        "total_cost_of_credit": round(total_interest + processing_fee_inr, 2)
    }
