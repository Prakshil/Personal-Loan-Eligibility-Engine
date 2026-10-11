# -*- coding: utf-8 -*-
"""
Rule Engine Module (Hybrid Enterprise Architecture)
---------------------------------------------------
Implements the multi-stage underwriting waterfall using pure CSV inputs:
Stage 1: Atomic Knockout Rules Filter (~520 atomic rules with rule_id audit logging).
Stage 2: Risk-Based Pricing Engine (Credit Score & Risk Tier Rate Mapping).
Stage 3: Debt-Capacity & Loan Sizing Engine (Dynamic FOIR Slabs & Employer Category Multiplier).
Stage 4: Credit card outstanding factor integration (5% balance obligation).
"""

import os
import re
import csv
from typing import Dict, Any, List, Tuple, Optional
from src.loan_calculator import (
    calculate_max_allowed_emi,
    calculate_effective_max_tenure,
    calculate_max_loan_by_foir,
    calculate_max_loan_by_multiplier,
    calculate_sanction_amount,
    calculate_loan_schedule_summary
)


DEFAULT_KNOCKOUT_RULES_PATH = os.path.join("data", "knockout_rules.csv")
DEFAULT_LENDER_MATRIX_PATH = os.path.join("data", "lender_rules_matrix.csv")


def load_atomic_knockout_rules(filepath: str = DEFAULT_KNOCKOUT_RULES_PATH) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load atomic knockout rules from data/knockout_rules.csv and group them by lender.

    Args:
        filepath: Path to knockout_rules.csv.

    Returns:
        Dictionary mapping lender identifier/name to a list of atomic rule dictionaries.
    """
    rules_by_lender: Dict[str, List[Dict[str, Any]]] = {}
    if not os.path.exists(filepath):
        return rules_by_lender

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lender_key = row["lender"].strip().lower()
            if lender_key not in rules_by_lender:
                rules_by_lender[lender_key] = []
            rules_by_lender[lender_key].append({
                "rule_id": row["rule_id"],
                "lender": row["lender"],
                "product_name": row["product_name"],
                "rule_family": row["rule_family"],
                "rule_name": row["rule_name"],
                "operator": row["operator"],
                "rule_value": row["rule_value"]
            })

    return rules_by_lender


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


def parse_numeric_fee(fee_str: str) -> float:
    """Extract numeric processing fee percentage from description string."""
    if not fee_str:
        return 1.5
    match = re.search(r"(\d+(\.\d+)?)%", fee_str)
    if match:
        return float(match.group(1))
    try:
        return float(fee_str)
    except ValueError:
        return 1.5


def load_lender_rules(filepath: str = DEFAULT_LENDER_MATRIX_PATH) -> List[Dict[str, Any]]:
    """
    Load lender underwriting policy definitions from CSV.
    Supports either the 24-column data/lender_rules_matrix.csv or legacy data/lender_rules.csv.

    Args:
        filepath: Path to lender policy CSV file.

    Returns:
        List of parsed lender configuration dictionaries.
    """
    # If default lender_rules_matrix.csv does not exist, fallback to lender_rules.csv
    if not os.path.exists(filepath):
        alt_path = os.path.join("data", "lender_rules.csv")
        if os.path.exists(alt_path):
            filepath = alt_path

    lenders = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check if this is the 24-column lender_rules_matrix.csv
            if "max_age_application" in row:
                foir_cap = float(row.get("foir_cap_pct", 55.0)) / 100.0
                mult_cap = float(row.get("salary_multiplier_cap", 20.0))
                start_rate = float(row.get("starting_interest_rate_pct", 11.0))
                ceil_rate = float(row.get("ceiling_interest_rate_pct", 15.0))
                spread = ceil_rate - start_rate

                foir_slabs = [
                    {"income_ceiling": 25000, "max_foir": max(0.40, round(foir_cap - 0.15, 2))},
                    {"income_ceiling": 50000, "max_foir": max(0.45, round(foir_cap - 0.10, 2))},
                    {"income_ceiling": 100000, "max_foir": max(0.50, round(foir_cap - 0.05, 2))},
                    {"income_ceiling": 999999999, "max_foir": foir_cap}
                ]

                salary_multipliers = {
                    "CAT_A": mult_cap,
                    "CAT_B": max(14.0, mult_cap - 2.0),
                    "CAT_C": max(10.0, mult_cap - 6.0),
                    "GOVERNMENT": mult_cap,
                    "GOVT": mult_cap
                }

                # Construct continuous risk pricing bands
                rate_bands = [
                    {"cibil_min": 780, "rate": round(start_rate, 2)},
                    {"cibil_min": 740, "rate": round(start_rate + 0.25 * spread, 2)},
                    {"cibil_min": 700, "rate": round(start_rate + 0.50 * spread, 2)},
                    {"cibil_min": 650, "rate": round(start_rate + 0.75 * spread, 2)},
                    {"cibil_min": 600, "rate": round(ceil_rate, 2)},
                    {"cibil_min": -1, "rate": round(ceil_rate, 2)}
                ]

                proc_fee_pct = parse_numeric_fee(row.get("processing_fee", "1.5%"))

                # In banking, maximum permissible applicant maturity age
                max_maturity_age = int(row.get("max_age_maturity", 60))
                max_app_age = int(row.get("max_age_application", 58))

                lender_dict = {
                    "lender_id": row["lender_id"],
                    "lender_name": row["lender_name"],
                    "product_name": row.get("product_name", "Personal Loan"),
                    "institution_type": row.get("category", "Private Sector Bank"),
                    "allowed_employment_types": ["Salaried"] if "Public" in row.get("category", "") else ["Salaried", "Self-Employed"],
                    "min_age": int(row["min_age"]),
                    "max_age_application": max_app_age,
                    "max_age": max_maturity_age,
                    "min_income_metro": float(row.get("min_monthly_salary_inr", 25000)),
                    "min_income_tier1": float(row.get("min_monthly_salary_inr", 20000)),
                    "min_income_non_metro": max(12000.0, float(row.get("min_monthly_salary_inr", 20000)) * 0.75),
                    "min_cibil": int(row["min_cibil_score"]),
                    "allow_ntc": int(row["min_cibil_score"]) <= 650 and ("Fintech" in row.get("category", "") or row["lender_id"] in ("navi", "kreditbee")),
                    "min_work_exp_months": int(row["min_work_exp_months"]),
                    "min_current_job_months": int(row["min_current_job_months"]),
                    "max_foir": foir_cap,
                    "foir_slabs": foir_slabs,
                    "max_salary_multiplier": mult_cap,
                    "salary_multipliers": salary_multipliers,
                    "min_tenure_months": int(row["min_tenure_months"]),
                    "max_tenure_months": int(row["max_tenure_months"]),
                    "min_loan_amount": float(row["min_loan_amount_inr"]),
                    "max_loan_amount": float(row["max_loan_amount_inr"]),
                    "base_rate": start_rate,
                    "ceiling_rate": ceil_rate,
                    "rate_bands": rate_bands,
                    "processing_fee_percent": proc_fee_pct,
                    "processing_fee_desc": row.get("processing_fee", ""),
                    "foreclosure_penalty": row.get("foreclosure_penalty", ""),
                    "source": row.get("primary_source_url", ""),
                    "accessed_date": row.get("accessed_on", ""),
                    "unlisted_rules_method_summary": row.get("unlisted_rules_method_summary", "")
                }
            else:
                # Fallback parser for standard lender_rules.csv
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
                    "product_name": row.get("product_name", "Personal Loan"),
                    "institution_type": row["institution_type"],
                    "allowed_employment_types": allowed_emp,
                    "min_age": int(row["min_age"]),
                    "max_age_application": int(row["max_age"]) - 2,
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
                    "ceiling_rate": float(row.get("base_rate", 12.0)) + 4.0,
                    "rate_bands": rate_bands,
                    "processing_fee_percent": float(row["processing_fee_percent"]),
                    "processing_fee_desc": f"{row['processing_fee_percent']}%",
                    "foreclosure_penalty": "2.0% - 4.0% prepayment penalty",
                    "source": row["source"],
                    "accessed_date": row["accessed_date"],
                    "unlisted_rules_method_summary": "Extracted from retail credit policy guidelines."
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
                "max_dpd_last_12m": int(row.get("max_dpd_last_12m", 0)),
                "hard_enquiries_last_30d": int(row.get("hard_enquiries_last_30d", 0)),
                "active_overdue_inr": float(row.get("active_overdue_inr", 0.0)),
                "written_off_accounts_count": int(row.get("written_off_accounts_count", 0)),
                "city_tier": row.get("city_tier", "Metro"),
                "desired_loan_amount": desired_loan,
                "desired_tenure_months": desired_tenure
            }
            profiles.append(p)
    return profiles


def resolve_dynamic_foir(lender: Dict[str, Any], monthly_income: float) -> float:
    """
    Resolve dynamic income-based FOIR slabs.

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
    Resolve employer category-aware salary multiplier.

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
    Calculate total effective monthly debt obligations factoring in
    running EMIs and standard 5% credit card balance load.

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
    Resolve the minimum required net income based on geographic city tier.
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

    Args:
        lender: Lender rule dictionary.
        cibil_score: Applicant CIBIL score (300-900 or -1).

    Returns:
        Applicable annual interest rate in percent.
    """
    rate_bands = lender.get("rate_bands", [])
    if not rate_bands:
        return float(lender.get("base_rate", 12.0))

    if cibil_score == -1:
        for band in rate_bands:
            if band.get("cibil_min") == -1:
                return float(band["rate"])
        return max(band["rate"] for band in rate_bands)

    sorted_bands = sorted(
        [b for b in rate_bands if b.get("cibil_min", 0) > 0],
        key=lambda x: x["cibil_min"],
        reverse=True
    )

    for band in sorted_bands:
        if cibil_score >= band["cibil_min"]:
            return float(band["rate"])

    return max(b["rate"] for b in rate_bands)


def evaluate_lender_knockouts(
    applicant: Dict[str, Any],
    lender: Dict[str, Any],
    atomic_rules: Optional[List[Dict[str, Any]]] = None
) -> Tuple[bool, List[str]]:
    """
    Perform Stage 1 Hard Knockout Policy checks for a single lender.
    Seamlessly integrates the ~520 atomic rules from data/knockout_rules.csv
    with explicit rule_id audit logging.

    Args:
        applicant: Dictionary of applicant demographic and financial variables.
        lender: Lender rule dictionary.
        atomic_rules: Optional list of atomic rules for this specific lender.

    Returns:
        Tuple of (is_pass: bool, rejection_reasons: List[str]).
    """
    reasons: List[str] = []

    age = applicant.get("age", 0)
    emp_type = applicant.get("employment_type", "Salaried")
    employer_cat = applicant.get("employer_category", "CAT_C")
    city_tier = applicant.get("city_tier", "Metro")
    monthly_income = float(applicant.get("monthly_net_income", 0.0))
    cibil = applicant.get("cibil_score", -1)

    total_exp = applicant.get("total_work_exp_months", applicant.get("total_work_experience_months", 0))
    current_tenure = applicant.get("current_job_tenure_months", 0)

    base_emis, cc_obligation, effective_emis = calculate_total_monthly_obligations(applicant)

    # Index atomic rules by rule_name if provided
    rules_map: Dict[str, Dict[str, Any]] = {}
    if atomic_rules:
        for r in atomic_rules:
            rules_map[r["rule_name"]] = r

    def get_rule_prefix(rname: str) -> str:
        if rname in rules_map:
            r = rules_map[rname]
            return f"[{r['rule_id']}] [{r['rule_family']}] "
        return ""

    # 1. Minimum Age Verification
    min_age = int(rules_map.get("min_age", {}).get("rule_value", lender.get("min_age", 21)))
    if age < min_age:
        reasons.append(
            f"{get_rule_prefix('min_age')}Applicant age {age} is below minimum required age of {min_age} years."
        )

    # 2. Maximum Application Age Verification
    max_app_age = int(rules_map.get("max_age_application", {}).get("rule_value", lender.get("max_age_application", 58)))
    if age > max_app_age:
        reasons.append(
            f"{get_rule_prefix('max_age_application')}Applicant age {age} exceeds maximum application age threshold of {max_app_age} years."
        )

    # 3. Maximum Maturity Age Verification
    max_mat_age = int(rules_map.get("max_age_maturity", {}).get("rule_value", lender.get("max_age", 60)))
    effective_max_tenure = calculate_effective_max_tenure(age, max_mat_age, lender.get("max_tenure_months", 60))
    min_tenure = lender.get("min_tenure_months", 12)
    if effective_max_tenure < min_tenure:
        reasons.append(
            f"{get_rule_prefix('max_age_maturity')}Remaining tenure to retirement/maturity age {max_mat_age} ({effective_max_tenure} mos) is below minimum product tenure ({min_tenure} mos)."
        )

    # 4. Employment Type Policy
    allowed_emp_val = rules_map.get("employment_type_allowed", {}).get("rule_value")
    if allowed_emp_val:
        allowed_emp_types = [t.strip().lower() for t in allowed_emp_val.split(",")]
    else:
        allowed_emp_types = [t.lower() for t in lender.get("allowed_employment_types", ["Salaried"])]

    app_emp_norm = emp_type.lower().replace("-", "_").replace(" ", "_")
    allowed_emp_norm = [t.replace("-", "_").replace(" ", "_") for t in allowed_emp_types]
    if app_emp_norm not in allowed_emp_norm:
        reasons.append(
            f"{get_rule_prefix('employment_type_allowed')}Employment type '{emp_type}' is not supported. Supported: {', '.join(allowed_emp_types)}."
        )

    # 5. Work Experience & Stability
    min_total_exp = int(rules_map.get("min_total_work_experience_months", {}).get("rule_value", lender.get("min_work_exp_months", 12)))
    if total_exp < min_total_exp:
        reasons.append(
            f"{get_rule_prefix('min_total_work_experience_months')}Total work experience ({total_exp} mos) is below required {min_total_exp} months."
        )

    is_gov = employer_cat.strip().upper() in ("GOVERNMENT", "GOVT", "DEFENCE", "CPSE")
    if is_gov and "min_current_job_tenure_government" in rules_map:
        min_cur = int(rules_map["min_current_job_tenure_government"]["rule_value"])
        if current_tenure < min_cur:
            reasons.append(
                f"{get_rule_prefix('min_current_job_tenure_government')}Current government tenure ({current_tenure} mos) is below required {min_cur} months."
            )
    else:
        min_cur = int(rules_map.get("min_current_job_tenure_corporate", {}).get("rule_value", lender.get("min_current_job_months", 6)))
        if current_tenure < min_cur:
            reasons.append(
                f"{get_rule_prefix('min_current_job_tenure_corporate')}Current job tenure ({current_tenure} mos) is below required {min_cur} months."
            )

    # 6. Minimum Income Requirement
    city_norm = city_tier.strip().lower().replace("-", "_").replace(" ", "_")
    if city_norm not in ("metro", "tier_1", "tier1") and "min_monthly_salary_non_metro" in rules_map:
        req_income = float(rules_map["min_monthly_salary_non_metro"]["rule_value"])
    elif is_gov and "min_monthly_salary_government" in rules_map:
        req_income = float(rules_map["min_monthly_salary_government"]["rule_value"])
    elif "min_monthly_salary_corporate" in rules_map:
        req_income = float(rules_map["min_monthly_salary_corporate"]["rule_value"])
    else:
        req_income = get_required_income_for_city(lender, city_tier)

    if monthly_income < req_income:
        rule_name_income = "min_monthly_salary_government" if is_gov else "min_monthly_salary_corporate"
        reasons.append(
            f"{get_rule_prefix(rule_name_income)}Monthly income ₹{monthly_income:,.0f} is below minimum requirement of ₹{req_income:,.0f}."
        )

    # 7. Credit Bureau Score & New-To-Credit (NTC) Policy
    min_cibil = int(rules_map.get("min_cibil_score", {}).get("rule_value", lender.get("min_cibil", 700)))
    allow_ntc_val = str(rules_map.get("allow_ntc_thin_file", {}).get("rule_value", str(lender.get("allow_ntc", False)))).strip().lower()
    allow_ntc = allow_ntc_val in ("true", "1", "yes")

    if cibil == -1:
        if not allow_ntc:
            reasons.append(
                f"{get_rule_prefix('allow_ntc_thin_file')}New-To-Credit (NTC / CIBIL -1) thin file is not eligible under lender bureau policy."
            )
    elif cibil < min_cibil:
        reasons.append(
            f"{get_rule_prefix('min_cibil_score')}CIBIL score {cibil} is below minimum bureau threshold of {min_cibil}."
        )

    # 8. CIR & DPD Bureau Delinquency and Credit Hunger Checks
    applicant_dpd = int(applicant.get("max_dpd_last_12m", 0))
    if "max_dpd_last_12m" in rules_map:
        allowed_dpd = int(rules_map["max_dpd_last_12m"]["rule_value"])
        if applicant_dpd > allowed_dpd:
            reasons.append(
                f"{get_rule_prefix('max_dpd_last_12m')}Bureau delinquency ({applicant_dpd} DPD in last 12m) exceeds maximum tolerance of {allowed_dpd} DPD."
            )

    applicant_enq = int(applicant.get("hard_enquiries_last_30d", 0))
    if "hard_enquiries_last_30d" in rules_map:
        max_enq = int(rules_map["hard_enquiries_last_30d"]["rule_value"])
        if applicant_enq > max_enq:
            reasons.append(
                f"{get_rule_prefix('hard_enquiries_last_30d')}High credit enquiry velocity ({applicant_enq} inquiries in 30d) exceeds maximum limit of {max_enq}."
            )

    active_overdue = float(applicant.get("active_overdue_inr", 0.0))
    if active_overdue > 0:
        reasons.append(
            f"{get_rule_prefix('active_overdue_inr')}Active overdue debt balance of ₹{active_overdue:,.0f} detected in bureau CIR (Zero overdue balance mandatory)."
        )

    written_off = int(applicant.get("written_off_accounts_count", 0))
    if written_off > 0:
        reasons.append(
            f"{get_rule_prefix('written_off_accounts_allowed')}Unsettled or written-off accounts ({written_off} found) detected in credit bureau report."
        )

    # 9. Dynamic FOIR Sizing Feasibility
    applicable_foir = resolve_dynamic_foir(lender, monthly_income)
    available_emi = calculate_max_allowed_emi(monthly_income, applicable_foir, effective_emis)
    if available_emi <= 0:
        foir_pct = int(applicable_foir * 100)
        reasons.append(
            f"FOIR breached: Total monthly obligations (₹{effective_emis:,.0f} including ₹{cc_obligation:,.0f} credit card factor) exceed or equal {foir_pct}% permissible salary limit."
        )

    return (len(reasons) == 0, reasons)


def underwrite_applicant_for_lender(
    applicant: Dict[str, Any],
    lender: Dict[str, Any],
    atomic_rules: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Execute the end-to-end 4-stage underwriting waterfall for an applicant against a lender.

    Args:
        applicant: Applicant profile dictionary.
        lender: Lender policy dictionary.
        atomic_rules: Optional list of atomic rules for this lender.

    Returns:
        Structured evaluation result.
    """
    passes_knockout, rejection_reasons = evaluate_lender_knockouts(applicant, lender, atomic_rules)

    if not passes_knockout:
        return {
            "lender_id": lender["lender_id"],
            "lender_name": lender["lender_name"],
            "product_name": lender.get("product_name", "Personal Loan"),
            "institution_type": lender["institution_type"],
            "is_eligible": False,
            "rejection_reasons": rejection_reasons,
            "financials": None,
            "unlisted_rules_method_summary": lender.get("unlisted_rules_method_summary", "")
        }

    # Stages 2 & 3: Risk Pricing and Debt Capacity Sizing
    age = applicant.get("age", 0)
    monthly_income = float(applicant.get("monthly_net_income", 0.0))
    cibil = applicant.get("cibil_score", -1)
    desired_loan = applicant.get("desired_loan_amount")
    desired_tenure = applicant.get("desired_tenure_months")
    employer_cat = applicant.get("employer_category", "CAT_C")

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
            "product_name": lender.get("product_name", "Personal Loan"),
            "institution_type": lender["institution_type"],
            "is_eligible": False,
            "rejection_reasons": [
                f"Calculated debt-capacity (₹{sanction_amount:,.0f}) is below minimum loan ticket ₹{lender_min_loan:,.0f}."
            ],
            "financials": None,
            "unlisted_rules_method_summary": lender.get("unlisted_rules_method_summary", "")
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
        "foreclosure_penalty": lender.get("foreclosure_penalty", "Standard prepayment terms"),
        "source": lender.get("source", ""),
        "accessed_date": lender.get("accessed_date", ""),
        "unlisted_rules_method_summary": lender.get("unlisted_rules_method_summary", "")
    })

    return {
        "lender_id": lender["lender_id"],
        "lender_name": lender["lender_name"],
        "product_name": lender.get("product_name", "Personal Loan"),
        "institution_type": lender["institution_type"],
        "is_eligible": True,
        "rejection_reasons": [],
        "financials": financial_summary,
        "unlisted_rules_method_summary": lender.get("unlisted_rules_method_summary", "")
    }


def underwrite_applicant_all_lenders(
    applicant: Dict[str, Any],
    lenders: List[Dict[str, Any]],
    atomic_rules_by_lender: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> List[Dict[str, Any]]:
    """
    Run underwriting waterfall for an applicant profile across all configured lenders.

    Args:
        applicant: Applicant profile dictionary.
        lenders: List of all 20 lender rule definitions.
        atomic_rules_by_lender: Optional dictionary of atomic rules grouped by lender.

    Returns:
        List of decision dictionaries for each lender.
    """
    if atomic_rules_by_lender is None:
        atomic_rules_by_lender = load_atomic_knockout_rules()

    results = []
    for lender in lenders:
        # Match lender atomic rules by name or id
        name_key = lender["lender_name"].strip().lower()
        rules = atomic_rules_by_lender.get(name_key)
        if not rules:
            for k, r_list in atomic_rules_by_lender.items():
                if lender["lender_id"].lower() in k or k in lender["lender_id"].lower():
                    rules = r_list
                    break
        res = underwrite_applicant_for_lender(applicant, lender, rules)
        results.append(res)
    return results
