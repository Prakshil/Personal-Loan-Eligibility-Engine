# -*- coding: utf-8 -*-
"""
Prescription Engine Module (What-If Counterfactual Recommendations)
-------------------------------------------------------------------
Implements counterfactual sensitivity analysis and deterministic borrower prescriptions:
1. Credit Card Balance Pay-Down: Simulates de-leveraging to release FOIR capacity.
2. Credit Score (CIBIL) Elevation: Computes rate savings and unlocked prime banks at CIBIL 720, 750, 780.
3. Job Vintage Horizon: Computes waiting period to clear current employer tenure hurdles.
4. Existing Debt Consolidation: Simulates pre-closing running EMIs to maximize loan sizing.
"""

from typing import Dict, Any, List, Optional
from src.rule_engine import underwrite_applicant_all_lenders
from src.ranker import rank_eligible_offers


def simulate_modified_profile(
    applicant: Dict[str, Any],
    lenders: List[Dict[str, Any]],
    modifications: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Helper to run underwriting on a cloned applicant profile with specific attribute modifications.
    """
    clone = dict(applicant)
    clone.update(modifications)
    evals = underwrite_applicant_all_lenders(clone, lenders)
    ranked = rank_eligible_offers(evals)
    best = ranked[0] if ranked else None
    return {
        "modified_applicant": clone,
        "evaluations": evals,
        "eligible_offers": ranked,
        "best_option": best,
        "approved_count": len(ranked)
    }


def generate_what_if_prescriptions(
    applicant: Dict[str, Any],
    lenders: List[Dict[str, Any]],
    current_decision: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Analyze the current underwriting decision and generate actionable,
    deterministic counterfactual prescriptions to unlock prime lenders,
    maximize sanction amounts, and minimize total borrowing costs.

    Args:
        applicant: Original applicant profile.
        lenders: List of all 20 lender definitions.
        current_decision: Output of get_recommendation_summary for the original profile.

    Returns:
        List of structured prescription recommendations sorted by borrower impact.
    """
    prescriptions: List[Dict[str, Any]] = []

    current_best = current_decision.get("best_option")
    current_rate = current_best["financials"]["interest_rate_pct"] if current_best else None
    current_sanction = current_best["financials"]["sanction_amount"] if current_best else 0.0
    current_approved_count = current_decision["summary"]["approved_count"]
    tenure = current_best["financials"]["tenure_months"] if current_best else int(applicant.get("desired_tenure_months") or 36)

    cibil = applicant.get("cibil_score", -1)
    cc_outstanding = float(applicant.get("credit_card_outstanding", 0.0))
    existing_emis = float(applicant.get("existing_monthly_emis", 0.0))
    cur_tenure = int(applicant.get("current_job_tenure_months", 0))
    tot_exp = int(applicant.get("total_work_exp_months", applicant.get("total_work_experience_months", 0)))
    monthly_income = float(applicant.get("monthly_net_income", 0.0))

    # -------------------------------------------------------------------------
    # 1. PRESCRIPTION: Credit Card Debt Pay-Down (De-leveraging)
    # -------------------------------------------------------------------------
    if cc_outstanding > 0:
        paydown_sim = simulate_modified_profile(applicant, lenders, {"credit_card_outstanding": 0.0})
        new_approved_count = paydown_sim["approved_count"]
        new_best = paydown_sim["best_option"]

        if new_best:
            new_sanction = new_best["financials"]["sanction_amount"]
            new_rate = new_best["financials"]["interest_rate_pct"]
            monthly_freed = round(cc_outstanding * 0.05, 2)
            capacity_gain = max(0.0, new_sanction - current_sanction)

            # Check if new lenders were unlocked
            current_lenders = {o["lender_id"] for o in current_decision.get("eligible_offers", [])}
            new_lenders = [o["lender_name"] for o in paydown_sim["eligible_offers"] if o["lender_id"] not in current_lenders]

            details = f"Paying off ₹{cc_outstanding:,.0f} credit card balance eliminates ₹{monthly_freed:,.0f}/mo phantom obligation."
            if new_lenders:
                details += f" Unlocks {len(new_lenders)} new lender(s): {', '.join(new_lenders[:3])}."
            if capacity_gain > 0:
                details += f" Expands borrowing capacity by +₹{capacity_gain:,.0f}."
            if current_rate and new_rate < current_rate:
                rate_diff = current_rate - new_rate
                interest_saved = (current_best["financials"]["monthly_emi"] - new_best["financials"]["monthly_emi"]) * tenure
                details += f" Lowers APR by {rate_diff:.2f}% (from {current_rate:.2f}% to {new_rate:.2f}%)."

            prescriptions.append({
                "type": "DELEVERAGING",
                "title": "Clear Credit Card Revolving Balance",
                "action": f"Pay down active credit card outstanding of ₹{cc_outstanding:,.0f}",
                "impact": f"+₹{capacity_gain:,.0f} Sanction Capacity" if capacity_gain > 0 else f"+{len(new_lenders)} Unlocked Lenders",
                "new_best_lender": new_best["lender_name"],
                "new_rate": new_rate,
                "explanation": details
            })

    # -------------------------------------------------------------------------
    # 2. PRESCRIPTION: Credit Score (CIBIL) Elevation Roadmap
    # -------------------------------------------------------------------------
    if cibil == -1:
        # New-to-Credit path
        ntc_sim = simulate_modified_profile(applicant, lenders, {"cibil_score": 750})
        new_best = ntc_sim["best_option"]
        if new_best:
            ntc_unlocked = [o["lender_name"] for o in ntc_sim["eligible_offers"]]
            rate_delta = (current_rate - new_best["financials"]["interest_rate_pct"]) if current_rate else 12.0
            interest_saved = (new_best["financials"]["sanction_amount"] * (rate_delta / 100.0) * (tenure / 12.0))
            prescriptions.append({
                "type": "CREDIT_BUILDING",
                "title": "Establish 6-Month Prime Credit Footprint",
                "action": "Open a secured credit card or consumer durables loan to establish a CIBIL 750 footprint",
                "impact": f"Unlocks {len(ntc_unlocked)} Banks (Saves ~₹{interest_saved:,.0f} Interest)",
                "new_best_lender": new_best["lender_name"],
                "new_rate": new_best["financials"]["interest_rate_pct"],
                "explanation": (
                    f"Currently restricted to high-cost fintechs (APR ~24%-29%). Building a score of 750 unlocks prime banks "
                    f"like {new_best['lender_name']} at {new_best['financials']['interest_rate_pct']:.2f}% p.a., saving approximately "
                    f"₹{interest_saved:,.0f} over a {tenure}-month tenure."
                )
            })
    elif cibil < 780:
        # Evaluate milestones: 720, 750, 780
        target_scores = [t for t in [720, 750, 780] if t > cibil]
        for target in target_scores:
            cibil_sim = simulate_modified_profile(applicant, lenders, {"cibil_score": target})
            new_best = cibil_sim["best_option"]
            if new_best:
                current_lenders = {o["lender_id"] for o in current_decision.get("eligible_offers", [])}
                unlocked_lenders = [o["lender_name"] for o in cibil_sim["eligible_offers"] if o["lender_id"] not in current_lenders]
                new_rate = new_best["financials"]["interest_rate_pct"]

                if (current_rate and new_rate < current_rate) or unlocked_lenders:
                    rate_savings = (current_rate - new_rate) if current_rate else 0.0
                    total_interest_saving = (current_best["financials"]["total_interest"] - new_best["financials"]["total_interest"]) if (current_best and current_best["financials"]["sanction_amount"] == new_best["financials"]["sanction_amount"]) else 0.0

                    explanation = f"Improving CIBIL from {cibil} to {target} (+{target - cibil} pts)"
                    if unlocked_lenders:
                        explanation += f" unlocks {len(unlocked_lenders)} prime institution(s): {', '.join(unlocked_lenders[:3])}."
                    if rate_savings > 0:
                        explanation += f" Reduces prime rate by {rate_savings:.2f}% p.a. down to {new_rate:.2f}%."

                    prescriptions.append({
                        "type": "CIBIL_ELEVATION",
                        "title": f"Elevate Credit Score to CIBIL {target}",
                        "action": f"Maintain on-time payments for 3-6 months to boost score by +{target - cibil} points",
                        "impact": f"-{rate_savings:.2f}% Interest Rate" if rate_savings > 0 else f"+{len(unlocked_lenders)} Prime Lenders",
                        "new_best_lender": new_best["lender_name"],
                        "new_rate": new_rate,
                        "explanation": explanation
                    })
                    break  # Focus on the closest actionable target

    # -------------------------------------------------------------------------
    # 3. PRESCRIPTION: Employment Stability Horizon (Waiting Period)
    # -------------------------------------------------------------------------
    if cur_tenure < 12:
        # Check impact of reaching 6 months or 12 months
        target_tenures = [t for t in [6, 12] if t > cur_tenure]
        for target_m in target_tenures:
            tenure_sim = simulate_modified_profile(applicant, lenders, {
                "current_job_tenure_months": target_m,
                "total_work_exp_months": tot_exp + (target_m - cur_tenure),
                "total_work_experience_months": tot_exp + (target_m - cur_tenure)
            })
            new_best = tenure_sim["best_option"]
            current_lenders = {o["lender_id"] for o in current_decision.get("eligible_offers", [])}
            unlocked_lenders = [o["lender_name"] for o in tenure_sim["eligible_offers"] if o["lender_id"] not in current_lenders]

            if unlocked_lenders and new_best:
                months_needed = target_m - cur_tenure
                prescriptions.append({
                    "type": "EMPLOYMENT_VINTAGE",
                    "title": f"Complete {target_m} Months at Current Employer",
                    "action": f"Wait {months_needed} additional month(s) with current organization",
                    "impact": f"+{len(unlocked_lenders)} Unlocked Institutional Lenders",
                    "new_best_lender": new_best["lender_name"],
                    "new_rate": new_best["financials"]["interest_rate_pct"],
                    "explanation": (
                        f"Reaching {target_m} months tenure clears strict employment stability hurdles, "
                        f"unlocking {len(unlocked_lenders)} top lender(s): {', '.join(unlocked_lenders[:3])} "
                        f"at rates starting at {new_best['financials']['interest_rate_pct']:.2f}%."
                    )
                })
                break

    # -------------------------------------------------------------------------
    # 4. PRESCRIPTION: Existing EMI Pre-closure / Restructuring
    # -------------------------------------------------------------------------
    if existing_emis > 0 and (current_approved_count < 10 or current_sanction < 300000):
        # Simulate pre-closing 50% of existing EMIs
        halved_emis = round(existing_emis * 0.50, 2)
        emi_sim = simulate_modified_profile(applicant, lenders, {"existing_monthly_emis": halved_emis})
        new_best = emi_sim["best_option"]

        if new_best:
            new_sanction = new_best["financials"]["sanction_amount"]
            capacity_gain = new_sanction - current_sanction
            current_lenders = {o["lender_id"] for o in current_decision.get("eligible_offers", [])}
            unlocked_lenders = [o["lender_name"] for o in emi_sim["eligible_offers"] if o["lender_id"] not in current_lenders]

            if capacity_gain > 50000 or unlocked_lenders:
                prescriptions.append({
                    "type": "DEBT_RESTRUCTURING",
                    "title": "Pre-close or Restructure Running Loans",
                    "action": f"Foreclose running loans to reduce existing monthly EMIs from ₹{existing_emis:,.0f} to ₹{halved_emis:,.0f}",
                    "impact": f"+₹{capacity_gain:,.0f} Loan Eligibility",
                    "new_best_lender": new_best["lender_name"],
                    "new_rate": new_best["financials"]["interest_rate_pct"],
                    "explanation": (
                        f"Relieving ₹{existing_emis - halved_emis:,.0f} in monthly debt obligations significantly increases available FOIR capacity, "
                        f"raising maximum loan sanction from ₹{current_sanction:,.0f} to ₹{new_sanction:,.0f}."
                    )
                })

    return prescriptions


def format_prescriptions_report(prescriptions: List[Dict[str, Any]]) -> str:
    """
    Format borrower prescriptions into an elegant CLI report section.
    """
    if not prescriptions:
        return ""

    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("⚡ ACTIONABLE WHAT-IF PRESCRIPTIONS & BORROWER OPTIMIZATION ROADMAP")
    lines.append("=" * 80)
    lines.append("The engine identified the following concrete actions to unlock prime lenders and minimize borrowing costs:")

    for idx, p in enumerate(prescriptions, start=1):
        lines.append(f"\n[{idx}] {p['title'].upper()} ({p['impact']})")
        lines.append(f"    • Recommended Action : {p['action']}")
        lines.append(f"    • Potential Partner   : {p['new_best_lender']} (Rate: {p['new_rate']:.2f}% p.a.)")
        lines.append(f"    • Underwriting Impact : {p['explanation']}")

    lines.append("\n" + "-" * 80)
    return "\n".join(lines)
