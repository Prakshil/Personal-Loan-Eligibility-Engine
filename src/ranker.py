"""
Ranker & Recommendation Engine Module
---------------------------------------
Implements Stage 4 of the underwriting waterfall:
1. Filters eligible offers vs. hard rejections.
2. Sorts eligible offers using a multi-criteria optimization hierarchy:
   - Primary: Lowest Annual Interest Rate (Lowest APR / cost of borrowing).
   - Secondary: Lowest Total Cost of Credit (Interest + Upfront Processing Fees).
   - Tertiary: Highest Sanction Capacity (Maximum financial flexibility).
3. Identifies the optimal "Best Option" lender recommendation.
4. Formats underwriting decision outputs for CLI reports and CSV exports.
"""

from typing import Dict, Any, List, Optional
from tabulate import tabulate


def rank_eligible_offers(evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort eligible lender offers according to borrower-centric optimization hierarchy.

    Ranking Criteria:
        1. Lowest interest rate (APR percentage).
        2. Lowest total cost of credit (total interest + processing fee).
        3. Highest sanction loan capacity.

    Args:
        evaluations: List of underwriting evaluation dictionaries.

    Returns:
        Sorted list of eligible lender evaluations with an added 'rank' field.
    """
    eligible = [ev for ev in evaluations if ev.get("is_eligible", False)]

    # Multi-key sorting
    sorted_eligible = sorted(
        eligible,
        key=lambda ev: (
            ev["financials"]["interest_rate_pct"],
            ev["financials"]["total_cost_of_credit"],
            -ev["financials"]["max_capacity_inr"]
        )
    )

    # Assign sequential ranks (1-indexed)
    for rank_idx, offer in enumerate(sorted_eligible, start=1):
        offer["rank"] = rank_idx

    return sorted_eligible


def get_recommendation_summary(
    evaluations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Produce a holistic recommendation decision payload for an applicant.

    Args:
        evaluations: List of evaluations across all 20 lenders.

    Returns:
        Dictionary containing best option, ranked eligible offers,
        ineligible lender breakdowns, and summary statistics.
    """
    eligible_ranked = rank_eligible_offers(evaluations)
    ineligible = [ev for ev in evaluations if not ev.get("is_eligible", False)]

    best_option: Optional[Dict[str, Any]] = eligible_ranked[0] if eligible_ranked else None

    total_lenders = len(evaluations)
    approved_count = len(eligible_ranked)
    rejected_count = len(ineligible)
    approval_rate = round((approved_count / total_lenders) * 100.0, 1) if total_lenders > 0 else 0.0

    return {
        "summary": {
            "total_lenders_evaluated": total_lenders,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "approval_rate_percent": approval_rate,
            "has_eligible_offers": approved_count > 0
        },
        "best_option": best_option,
        "eligible_offers": eligible_ranked,
        "ineligible_lenders": ineligible
    }


def format_underwriting_report(
    applicant: Dict[str, Any],
    decision_summary: Dict[str, Any]
) -> str:
    """
    Generate an ASCII underwriting report suitable for production CLI logging.

    Args:
        applicant: Applicant profile dictionary.
        decision_summary: Summary dictionary from get_recommendation_summary.

    Returns:
        Formatted multi-section report string.
    """
    lines: List[str] = []
    lines.append("=" * 80)
    lines.append("PERSONAL LOAN UNDERWRITING & WATERFALL RECOMMENDATION REPORT")
    lines.append("=" * 80)

    # Applicant Profile Section
    cibil_display = "NTC (Thin-File: -1)" if applicant.get("cibil_score") == -1 else str(applicant.get("cibil_score"))
    tot_exp = applicant.get("total_work_exp_months", applicant.get("total_work_experience_months", 0))
    cur_exp = applicant.get("current_job_tenure_months", 0)
    cc_outstanding = float(applicant.get("credit_card_outstanding", 0.0))
    cc_load = round(cc_outstanding * 0.05, 2)
    base_emis = float(applicant.get("existing_monthly_emis", 0.0))

    lines.append("\n[APPLICANT PROFILE]")
    lines.append(f"  Name / ID         : {applicant.get('name', applicant.get('applicant_id', applicant.get('profile_id', 'Unknown')))}")
    lines.append(f"  Age               : {applicant.get('age')} years")
    lines.append(f"  Employment Type   : {applicant.get('employment_type')} ({applicant.get('employer_category', 'N/A')})")
    lines.append(f"  Monthly Net Income: ₹{applicant.get('monthly_net_income', 0):,.0f}")
    if cc_outstanding > 0:
        lines.append(f"  Monthly Debt Load : ₹{base_emis + cc_load:,.0f} (EMIs: ₹{base_emis:,.0f} + 5% of Card Balance ₹{cc_outstanding:,.0f})")
    else:
        lines.append(f"  Existing EMIs     : ₹{base_emis:,.0f}")
    lines.append(f"  Credit Bureau     : CIBIL {cibil_display}")
    lines.append(f"  Work Experience   : {tot_exp} mos total | {cur_exp} mos current")
    lines.append(f"  Location          : {applicant.get('city_tier', 'Metro')}")
    if applicant.get("desired_loan_amount"):
        lines.append(f"  Requested Loan    : ₹{applicant.get('desired_loan_amount', 0):,.0f} for {applicant.get('desired_tenure_months', 0)} months")

    # Overview Metrics
    summ = decision_summary["summary"]
    lines.append("\n[UNDERWRITING SUMMARY]")
    lines.append(f"  Lenders Evaluated : {summ['total_lenders_evaluated']}")
    lines.append(f"  Approved          : {summ['approved_count']} ({summ['approval_rate_percent']}%)")
    lines.append(f"  Rejected          : {summ['rejected_count']}")

    # Best Option Highlight
    best = decision_summary["best_option"]
    if best:
        fin = best["financials"]
        foir_applied = fin.get("effective_foir_applied", 0.50) * 100
        mult_applied = fin.get("salary_multiplier_applied", 18.0)
        lines.append("\n" + "*" * 80)
        lines.append(f"★ BEST RECOMMENDED OPTION: {best['lender_name']} ({best['institution_type']})")
        lines.append("*" * 80)
        lines.append(f"  Approved Sanction Amount : ₹{fin['sanction_amount']:,.0f}")
        lines.append(f"  Applicable Interest Rate : {fin['interest_rate_pct']:.2f}% p.a.")
        lines.append(f"  Approved Loan Tenure     : {fin['tenure_months']} months")
        lines.append(f"  Equated Monthly EMI      : ₹{fin['monthly_emi']:,.0f}/month")
        lines.append(f"  Dynamic Underwriting     : FOIR {foir_applied:.0f}% slab | Salary Multiplier {mult_applied:.0f}x")
        lines.append(f"  Total Interest Outflow   : ₹{fin['total_interest']:,.0f}")
        lines.append(f"  Processing Fee           : ₹{fin['processing_fee_inr']:,.0f} ({fin['processing_fee_pct']}%)")
        lines.append(f"  Total Cost of Credit     : ₹{fin['total_cost_of_credit']:,.0f}")
        lines.append(f"  Max Possible Capacity    : ₹{fin['max_capacity_inr']:,.0f}")
        if fin.get("foreclosure_penalty"):
            lines.append(f"  Foreclosure Terms        : {fin['foreclosure_penalty']}")
        if fin.get("unlisted_rules_method_summary"):
            lines.append(f"  Unlisted Rules Policy    : {fin['unlisted_rules_method_summary']}")
        lines.append(f"  Source Verification      : {fin['source']} (as of {fin['accessed_date']})")
    else:
        lines.append("\n" + "!" * 80)
        lines.append("NO ELIGIBLE LENDERS FOUND FOR THIS APPLICANT PROFILE")
        lines.append("!" * 80)

    # Eligible Offers Table
    if decision_summary["eligible_offers"]:
        lines.append("\n[ALL ELIGIBLE OFFERS - RANKED BY LOWEST RATE & COST]")
        table_data = []
        for offer in decision_summary["eligible_offers"]:
            f = offer["financials"]
            table_data.append([
                f"#{offer['rank']}",
                offer["lender_name"],
                offer["institution_type"],
                f"{f['interest_rate_pct']:.2f}%",
                f"₹{f['sanction_amount']:,.0f}",
                f"{f['tenure_months']}m",
                f"₹{f['monthly_emi']:,.0f}",
                f"₹{f['processing_fee_inr']:,.0f}",
                f"₹{f['total_cost_of_credit']:,.0f}"
            ])
        headers = ["Rank", "Lender", "Type", "Rate", "Sanction", "Tenure", "EMI", "Proc Fee", "Total Cost"]
        lines.append(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Ineligible Reasons Table
    if decision_summary["ineligible_lenders"]:
        lines.append("\n[INELIGIBLE LENDERS & EXPLICIT REJECTION REASONS]")
        ineligible_data = []
        for inelig in decision_summary["ineligible_lenders"]:
            reasons_text = "\n• ".join([""] + inelig["rejection_reasons"]).strip()
            ineligible_data.append([
                inelig["lender_name"],
                inelig["institution_type"],
                reasons_text
            ])
        headers = ["Lender", "Type", "Underwriting Rejection Reasons"]
        lines.append(tabulate(ineligible_data, headers=headers, tablefmt="grid"))

    lines.append("\n" + "=" * 80 + "\n")
    return "\n".join(lines)
