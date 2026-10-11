# -*- coding: utf-8 -*-
"""
Rule Engine Module (Pure CSV Architecture)
------------------------------------------
Implements the multi-stage underwriting waterfall using pure CSV inputs:
Stage 1: Hard Knockout Rules Filter (hard criteria eligibility check).
Stage 2: Risk-Based Pricing Engine (Credit Score & Risk Tier Rate Mapping).
Stage 3: Debt-Capacity & Loan Sizing Engine (Dynamic FOIR Slabs & Employer Category Multiplier).
Stage 4: Credit card outstanding factor integration (5% balance obligation).
"""

import csv
from typing import Dict, Any, List, Tuple
from src.loan_calculator import (
    calculate_max_allowed_emi,
    calculate_effective_max_tenure,
    calculate_max_loan_by_foir,
    calculate_max_loan_by_multiplier,
    calculate_sanction_amount,
    calculate_loan_schedule_summary
)


def parse_rate_bands_string(rate_bands_str: str) -> List[Dict[str, Any]]:
    """
    Parse pure CSV rate band string (e.g. '800:11.15;750:11.65;720:12.40').

    Args:
        rate_bands_str: Semicolon-delimited 'cibil_threshold:rate' pairs.

    Returns:
        List of rate band dictionaries with cibil_min and rate.
    """
    bands = []
    if not rate_bands_str:
        return bands
    for part in rate_bands_str.split(";"):
        item = part.strip()
        if ":" in item:
            cibil_part, rate_part = item.split(":")
            bands.append({
                "cibil_min": int(cibil_part.strip()),
                "rate": float(rate_part.strip())
            })
    return bands


def load_lender_rules(filepath: str) -> List[Dict[str, Any]]:
    """
    Load lender underwriting policy definitions from a pure CSV configuration file.

    Args:
        filepath: Path to lender_rules.csv.

    Returns:
        List of parsed lender configuration dictionaries.
    """
    lenders = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse pure CSV columns
            rate_bands = parse_rate_bands_string(row.get("rate_bands", ""))

            foir_slabs = [
                {"income_ceiling": 25000, "max_foir": float(row.get("foir_upto_25k", 0.40))},
                {"income_ceiling": 50000, "max_foir": float(row.get("foir_upto_50k", 0.50))},
                {"income_ceiling": 100000, "max_foir": float(row.get("foir_upto_100k", 0.55))},
                {"income_ceiling": 999999999, "max_foir": float(row.get("foir_above_100k", 0.60))}
            ]

            salary_multipliers = {
                "CAT_A": float(row.get("multiplier_cat_a", 20.0)),
                "CAT_B": float(row.get("multiplier_cat_b", 18.0)),
                "CAT_C": float(row.get("multiplier_cat_c", 14.0)),
                "GOVERNMENT": float(row.get("multiplier_govt", 20.0)),
                "GOVT": float(row.get("multiplier_govt", 20.0))
            }

            emp_types_str = row.get("allowed_employment_types", "Salaried")
            allowed_emp = [s.strip() for s in emp_types_str.split(";") if s.strip()]

            allow_ntc_bool = str(row.get("allow_ntc", "FALSE")).strip().upper() in ("TRUE", "1", "YES")

            lender_dict = {
                "lender_id": row["lender_id"],
                "lender_name": row["lender_name"],
                "institution_type": row["institution_type"],
                "allowed_employment_types": allowed_emp,
                "min_age": int(row["min_age"]),
                "max_age": int(row["max_age"]),
                "min_income_metro": float(row["min_income_metro"]),
                "min_income_tier1": float(row["min_income_tier1"]),
                "min_income_non_metro": float(row.get("min_income_non_metro", 15000)),
                "min_cibil": int(row["min_cibil"]),
                "allow_ntc": allow_ntc_bool,
                "min_work_exp_months": int(row["min_work_exp_months"]),
                "min_current_job_months": int(row["min_current_job_months"]),
                "max_foir": float(row.get("foir_above_100k", 0.50)),
                "foir_slabs": foir_slabs,
                "max_salary_multiplier": float(row.get("multiplier_cat_b", 18.0)),
                "salary_multipliers": salary_multipliers,
                "min_tenure_months": int(row["min_tenure_months"]),
                "max_tenure_months": int(row["max_tenure_months"]),
                "min_loan_amount": float(row["min_loan_amount"]),
                "max_loan_amount": float(row["max_loan_amount"]),
                "base_rate": float(row["base_rate"]),
                "rate_bands": rate_bands,
                "processing_fee_percent": float(row["processing_fee_percent"]),
                "source": row["source"],
                "accessed_date": row["accessed_date"]
            }
            lenders.append(lender_dict)
    return lenders


def load_applicant_profiles(filepath: str) -> List[Dict[str, Any]]:
    """
    Load applicant profiles from a pure CSV file.

    Args:
        filepath: Path to test_profiles.csv.

    Returns:
        List of applicant profile dictionaries.
    """
    profiles = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            desired_loan = float(row["desired_loan_amount"]) if row.get("desired_loan_amount") and row["desired_loan_amount"].strip() else None
            desired_tenure = int(row["desired_tenure_months"]) if row.get("desired_tenure_months") and row["desired_tenure_months"].strip() else None

            p = {
                "applicant_id": row.get("applicant_id", row.get("profile_id", "")),
                "profile_id": row.get("profile_id", row.get("applicant_id", "")),
                "name": row.get("name", ""),
                "description": row.get("description", ""),
                "age": int(row.get("age", 0)),
                "employment_type": row.get("employment_type", "Salaried"),
                "employer_category": row.get("employer_category", "CAT_C"),
                "total_work_exp_months": int(row.get("total_work_exp_months", row.get("total_work_experience_months", 0))),
                "total_work_experience_months": int(row.get("total_work_experience_months", row.get("total_work_exp_months", 0))),
                "current_job_tenure_months": int(row.get("current_job_tenure_months", 0)),
                "monthly_net_income": float(row.get("monthly_net_income", 0.0)),
                "existing_monthly_emis": float(row.get("existing_monthly_emis", 0.0)),
                "credit_card_outstanding": float(row.get("credit_card_outstanding", 0.0)),
                "cibil_score": int(row.get("cibil_score", -1)),
                "city_tier": row.get("city_tier", "Metro"),
                "desired_loan_amount": desired_loan,
                "desired_tenure_months": desired_tenure
            }
            profiles.append(p)
    return profiles


def resolve_dynamic_foir(lender: Dict[str, Any], monthly_income: float) -> float:
    """
    Upgrade A: Resolve dynamic income-based FOIR slabs.
    In real-world retail banking, lower income brackets are assigned lower FOIRs (e.g. 40%)
    to safeguard basic living expenses, whereas high earners are permitted higher FOIRs (up to 60-65%).

    Args:
        lender: Lender policy dictionary.
        monthly_income: Verified monthly net salary in INR.

    Returns:
        Applicable maximum FOIR as a float decimal (e.g. 0.50).
    """
    foir_slabs = lender.get("foir_slabs", [])
    if not foir_slabs:
        return float(lender.get("max_foir", 0.50))

    sorted_slabs = sorted(foir_slabs, key=lambda x: x["income_ceiling"])
    for slab in sorted_slabs:
        if monthly_income <= slab["income_ceiling"]:
            return float(slab["max_foir"])

    return float(sorted_slabs[-1]["max_foir"])


def resolve_salary_multiplier(lender: Dict[str, Any], employer_category: str) -> float:
    """
    Upgrade B: Resolve employer category-aware salary multiplier.
    Fortune 500 / CAT-A corporate employees receive prime multipliers (20x-24x),
    while CAT-C / unlisted corporate employees receive conservative caps (12x-16x).

    Args:
        lender: Lender policy dictionary.
        employer_category: Category string (e.g., CAT-A, CAT_A, CAT-B, Government).

    Returns:
        Applicable salary multiplier as a float.
    """
    employer_norm = (employer_category or "CAT-C").strip().upper().replace("-", "_")
    multipliers_dict = lender.get("salary_multipliers", {})

    if multipliers_dict:
        if employer_norm in multipliers_dict:
            return float(multipliers_dict[employer_norm])
        if employer_norm in ("GOVERNMENT", "GOVT"):
            return float(multipliers_dict.get("GOVERNMENT", multipliers_dict.get("GOVT", 20.0)))
        return float(multipliers_dict.get("CAT_C", lender.get("max_salary_multiplier", 18.0)))

    return float(lender.get("max_salary_multiplier", 18.0))


def calculate_total_monthly_obligations(applicant: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Upgrade C: Calculate total effective monthly debt obligations by factoring in
    both running loan EMIs and a 5% credit card outstanding liability load factor.

    Formula:
        Total Monthly Obligations = Existing Monthly EMIs + (Credit Card Outstanding * 5%)

    Args:
        applicant: Applicant profile dictionary.

    Returns:
        Tuple of (base_emis, cc_obligation, total_effective_emis).
    """
    base_emis = float(applicant.get("existing_monthly_emis", 0.0))
    cc_outstanding = float(applicant.get("credit_card_outstanding", 0.0))
    cc_obligation = round(cc_outstanding * 0.05, 2)
    total_effective_emis = round(base_emis + cc_obligation, 2)
    return (base_emis, cc_obligation, total_effective_emis)


def get_required_income_for_city(lender: Dict[str, Any], city_tier: str) -> float:
    """
    Resolve the minimum required net income based on the applicant's geographic city tier.

    Args:
        lender: Lender rule dictionary.
        city_tier: Metro, Non-Metro, Tier 1, or Tier 2.

    Returns:
        Required monthly net income in INR.
    """
    city_normalized = (city_tier or "Metro").strip().lower().replace("-", "_").replace(" ", "_")
    if city_normalized in ("metro",):
        return float(lender.get("min_income_metro", 25000))
    elif city_normalized in ("tier_1", "tier1"):
        return float(lender.get("min_income_tier1", 20000))
    else:
        return float(lender.get("min_income_non_metro", 15000))


def resolve_applicable_interest_rate(lender: Dict[str, Any], cibil_score: int) -> float:
    """
    Map an applicant's CIBIL score to the lender's risk-based pricing bands.

    Lenders assign lower interest rates to higher credit scores (CIBIL >= 780),
    progressively widening rate spreads for lower bands or New-To-Credit (-1).

    Args:
        lender: Lender rule dictionary.
        cibil_score: Applicant CIBIL score (300-900 or -1).

    Returns:
        Applicable annual interest rate in percent.
    """
    rate_bands = lender.get("rate_bands", [])
    if not rate_bands:
        return float(lender.get("base_rate", 12.0))

    # Handle New-To-Credit (-1)
    if cibil_score == -1:
        for band in rate_bands:
            if band.get("cibil_min") == -1:
                return float(band["rate"])
        # If no specific NTC band, default to highest rate band
        return max(band["rate"] for band in rate_bands)

    # Sort rate bands by cibil_min descending
    sorted_bands = sorted(
        [b for b in rate_bands if b.get("cibil_min", 0) > 0],
        key=lambda x: x["cibil_min"],
        reverse=True
    )

    for band in sorted_bands:
        if cibil_score >= band["cibil_min"]:
            return float(band["rate"])

    # Fallback to the highest rate in the bands or base rate
    return max(b["rate"] for b in rate_bands)


def evaluate_lender_knockouts(
    applicant: Dict[str, Any],
    lender: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Perform Stage 1 Hard Knockout Policy checks for a single lender.

    Evaluates:
    1. Demographics: Minimum & maximum permissible age.
    2. Employment: Permissible employment types (Salaried vs. Self-Employed).
    3. Location-tiered Income: Minimum net in-hand monthly salary.
    4. Credit History: Bureau score threshold and NTC acceptance.
    5. Job Stability: Total work experience and current job tenure.
    6. Debt Capacity: Available surplus after existing monthly obligations (Dynamic FOIR).

    Args:
        applicant: Dictionary of applicant demographic and financial variables.
        lender: Lender rule dictionary.

    Returns:
        Tuple of (is_pass: bool, rejection_reasons: List[str]).
    """
    reasons: List[str] = []

    age = applicant.get("age", 0)
    emp_type = applicant.get("employment_type", "")
    city_tier = applicant.get("city_tier", "Metro")
    monthly_income = float(applicant.get("monthly_net_income", 0.0))
    cibil = applicant.get("cibil_score", -1)

    total_exp = applicant.get("total_work_exp_months", applicant.get("total_work_experience_months", 0))
    current_tenure = applicant.get("current_job_tenure_months", 0)

    base_emis, cc_obligation, effective_emis = calculate_total_monthly_obligations(applicant)

    # 1. Age Verification
    min_age = lender.get("min_age", 21)
    max_age = lender.get("max_age", 60)
    if age < min_age:
        reasons.append(f"Age {age} is below minimum required age of {min_age} years.")
    elif age >= max_age:
        reasons.append(f"Age {age} exceeds or matches maximum permissible maturity age of {max_age} years.")

    # 2. Employment Type Policy
    allowed_emp_types = [t.lower() for t in lender.get("allowed_employment_types", ["Salaried"])]
    applicant_emp_norm = emp_type.lower().replace("-", "_").replace(" ", "_")
    allowed_emp_norm = [t.replace("-", "_").replace(" ", "_") for t in allowed_emp_types]
    if applicant_emp_norm not in allowed_emp_norm:
        reasons.append(
            f"Employment type '{emp_type}' is not supported. Lender only accepts: {', '.join(lender.get('allowed_employment_types', ['Salaried']))}."
        )

    # 3. Minimum Monthly Income Requirement
    required_income = get_required_income_for_city(lender, city_tier)
    if monthly_income < required_income:
        reasons.append(
            f"Monthly income ₹{monthly_income:,.0f} is below minimum required ₹{required_income:,.0f} for {city_tier}."
        )

    # 4. Credit Bureau (CIBIL) & NTC Policy
    min_cibil = lender.get("min_cibil", 700)
    allow_ntc = lender.get("allow_ntc", False)

    if cibil == -1:
        if not allow_ntc:
            reasons.append("New-To-Credit (NTC / CIBIL -1) is not eligible under lender bureau policy.")
    elif cibil < min_cibil:
        reasons.append(f"CIBIL score {cibil} is below minimum threshold of {min_cibil}.")

    # 5. Employment Stability Checks
    min_total_exp = lender.get("min_work_exp_months", 12)
    min_current_exp = lender.get("min_current_job_months", 6)
    if total_exp < min_total_exp:
        reasons.append(
            f"Total work experience ({total_exp} mos) is below required {min_total_exp} months."
        )
    if current_tenure < min_current_exp:
        reasons.append(
            f"Current employer tenure ({current_tenure} mos) is below required {min_current_exp} months."
        )

    # 6. Upgrade A: Dynamic FOIR / Debt-Burden Feasibility
    applicable_foir = resolve_dynamic_foir(lender, monthly_income)
    available_emi = calculate_max_allowed_emi(monthly_income, applicable_foir, effective_emis)
    if available_emi <= 0:
        foir_pct = int(applicable_foir * 100)
        reasons.append(
            f"FOIR breached: Total monthly obligations (₹{effective_emis:,.0f} including ₹{cc_obligation:,.0f} card factor) consume >= {foir_pct}% of net income."
        )

    # 7. Retirement Tenure Feasibility
    effective_max_tenure = calculate_effective_max_tenure(age, max_age, lender.get("max_tenure_months", 60))
    min_tenure = lender.get("min_tenure_months", 12)
    if effective_max_tenure < min_tenure:
        reasons.append(
            f"Remaining service life ({effective_max_tenure} mos) is below minimum product tenure ({min_tenure} mos)."
        )

    return (len(reasons) == 0, reasons)


def underwrite_applicant_for_lender(
    applicant: Dict[str, Any],
    lender: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute the end-to-end 4-stage underwriting waterfall for an applicant against a lender.

    Args:
        applicant: Applicant profile dictionary.
        lender: Lender policy dictionary.

    Returns:
        Structured evaluation result including decision status, rejection reasons,
        pricing, sanction sizing, and repayment summary.
    """
    passes_knockout, rejection_reasons = evaluate_lender_knockouts(applicant, lender)

    if not passes_knockout:
        return {
            "lender_id": lender["lender_id"],
            "lender_name": lender["lender_name"],
            "institution_type": lender["institution_type"],
            "is_eligible": False,
            "rejection_reasons": rejection_reasons,
            "financials": None
        }

    # Stage 2 & 3: Sizing and Pricing
    age = applicant.get("age", 0)
    monthly_income = float(applicant.get("monthly_net_income", 0.0))
    cibil = applicant.get("cibil_score", -1)
    desired_loan = applicant.get("desired_loan_amount")
    desired_tenure = applicant.get("desired_tenure_months")
    employer_cat = applicant.get("employer_category", "CAT-C")

    base_emis, cc_obligation, effective_emis = calculate_total_monthly_obligations(applicant)
    applicable_foir = resolve_dynamic_foir(lender, monthly_income)
    applicable_multiplier = resolve_salary_multiplier(lender, employer_cat)

    lender_max_tenure = int(lender.get("max_tenure_months", 60))
    lender_min_tenure = int(lender.get("min_tenure_months", 12))
    lender_max_age = int(lender.get("max_age", 60))
    lender_min_loan = float(lender.get("min_loan_amount", 25000))
    lender_max_loan = float(lender.get("max_loan_amount", 4000000))
    fee_pct = float(lender.get("processing_fee_percent", 1.5))

    applicable_rate = resolve_applicable_interest_rate(lender, cibil)
    effective_max_tenure = calculate_effective_max_tenure(age, lender_max_age, lender_max_tenure_months=lender_max_tenure)

    if desired_tenure and desired_tenure > 0:
        selected_tenure = min(desired_tenure, effective_max_tenure)
        selected_tenure = max(selected_tenure, lender_min_tenure)
    else:
        selected_tenure = effective_max_tenure

    available_emi = calculate_max_allowed_emi(monthly_income, applicable_foir, effective_emis)
    max_loan_foir = calculate_max_loan_by_foir(available_emi, applicable_rate, selected_tenure)
    max_loan_multiplier = calculate_max_loan_by_multiplier(monthly_income, applicable_multiplier)

    sanction_amount = calculate_sanction_amount(
        max_loan_foir=max_loan_foir,
        max_loan_multiplier=max_loan_multiplier,
        lender_max_loan=lender_max_loan,
        lender_min_loan=lender_min_loan,
        desired_loan_amount=desired_loan
    )

    if sanction_amount < lender_min_loan or sanction_amount <= 0:
        return {
            "lender_id": lender["lender_id"],
            "lender_name": lender["lender_name"],
            "institution_type": lender["institution_type"],
            "is_eligible": False,
            "rejection_reasons": [
                f"Calculated debt-capacity (₹{sanction_amount:,.0f}) is below minimum loan ticket ₹{lender_min_loan:,.0f}."
            ],
            "financials": None
        }

    theoretical_max_capacity = calculate_sanction_amount(
        max_loan_foir=max_loan_foir,
        max_loan_multiplier=max_loan_multiplier,
        lender_max_loan=lender_max_loan,
        lender_min_loan=lender_min_loan,
        desired_loan_amount=None
    )

    financial_summary = calculate_loan_schedule_summary(
        principal=sanction_amount,
        annual_interest_rate=applicable_rate,
        tenure_months=selected_tenure,
        processing_fee_percent=fee_pct
    )

    financial_summary.update({
        "max_capacity_inr": theoretical_max_capacity,
        "max_eligible_tenure_months": effective_max_tenure,
        "available_monthly_emi_capacity": available_emi,
        "effective_foir_applied": applicable_foir,
        "salary_multiplier_applied": applicable_multiplier,
        "credit_card_monthly_load": cc_obligation,
        "foir_utilized_pct": round(((effective_emis + financial_summary["monthly_emi"]) / monthly_income) * 100.0, 2),
        "source": lender.get("source", ""),
        "accessed_date": lender.get("accessed_date", "")
    })

    return {
        "lender_id": lender["lender_id"],
        "lender_name": lender["lender_name"],
        "institution_type": lender["institution_type"],
        "is_eligible": True,
        "rejection_reasons": [],
        "financials": financial_summary
    }


def underwrite_applicant_all_lenders(
    applicant: Dict[str, Any],
    lenders: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Run underwriting waterfall for an applicant profile across all configured lenders.

    Args:
        applicant: Applicant profile dictionary.
        lenders: List of all 20 lender rule definitions.

    Returns:
        List of decision dictionaries for each lender.
    """
    return [underwrite_applicant_for_lender(applicant, lender) for lender in lenders]
