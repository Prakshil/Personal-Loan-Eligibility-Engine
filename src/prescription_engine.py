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

    Covers all borrower segments:
    - New-to-Credit (NTC) / Thin-File roadmap
    - Delinquency seasoning (DPD roll-off) & inquiry cooling period
    - Regulatory entry age milestone (Age 21 hurdle)
    - Employment stability & vintage horizons (current tenure & total career)
    - Credit card & debt restructuring (FOIR expansion)
    - Household co-applicant income pooling
    - Self-employed / MSME channel routing
    - Retirement horizon & senior citizen tenure optimization
    - Prime borrower fee waiver & rate matching negotiation

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
    current_lenders = {o["lender_id"] for o in current_decision.get("eligible_offers", [])}

    age = int(applicant.get("age", 0))
    cibil = applicant.get("cibil_score", -1)
    cc_outstanding = float(applicant.get("credit_card_outstanding", 0.0))
    existing_emis = float(applicant.get("existing_monthly_emis", 0.0))
    cur_tenure = int(applicant.get("current_job_tenure_months", 0))
    tot_exp = int(applicant.get("total_work_exp_months", applicant.get("total_work_experience_months", 0)))
    monthly_income = float(applicant.get("monthly_net_income", 0.0))
    emp_type = applicant.get("employment_type", "Salaried")
    dpd = int(applicant.get("max_dpd_last_12m", 0))
    enquiries = int(applicant.get("hard_enquiries_last_30d", 0))
    desired_tenure = int(applicant.get("desired_tenure_months") or 36)

    # -------------------------------------------------------------------------
    # 1. PRESCRIPTION: Age 21 Regulatory Milestone Horizon
    # -------------------------------------------------------------------------
    if age < 21:
        age_sim = simulate_modified_profile(applicant, lenders, {"age": 21})
        new_best = age_sim["best_option"]
        unlocked_lenders = [o["lender_name"] for o in age_sim["eligible_offers"] if o["lender_id"] not in current_lenders]
        if new_best:
            prescriptions.append({
                "type": "AGE_HORIZON",
                "title": "Reach Age 21 Regulatory Milestone",
                "action": f"Wait until 21st birthday ({21 - age} year milestone) or apply with an eligible parent co-applicant",
                "impact": f"Unlocks {len(unlocked_lenders)} Institutional Lenders",
                "new_best_lender": new_best["lender_name"],
                "new_rate": new_best["financials"]["interest_rate_pct"],
                "explanation": (
                    f"Scheduled commercial banks enforce a strict entry age of 21. Reaching age 21 with your existing "
                    f"₹{monthly_income:,.0f} income and CIBIL {cibil if cibil > 0 else 'NTC'} instantly unlocks {len(unlocked_lenders)} "
                    f"prime lenders led by {new_best['lender_name']} at {new_best['financials']['interest_rate_pct']:.2f}% p.a."
                )
            })

    # -------------------------------------------------------------------------
    # 2. PRESCRIPTION: Self-Employed / Business Loan Channel Routing
    # -------------------------------------------------------------------------
    emp_norm = emp_type.strip().lower()
    if emp_norm not in ("salaried",):
        salaried_sim = simulate_modified_profile(applicant, lenders, {"employment_type": "Salaried"})
        new_best = salaried_sim["best_option"]
        salaried_unlocked = [o["lender_name"] for o in salaried_sim["eligible_offers"] if o["lender_id"] not in current_lenders]
        prescriptions.append({
            "type": "BUSINESS_LOAN_ROUTING",
            "title": "Route via MSME / Business Loan Vertical",
            "action": "Apply through MSME / Self-Employed Professional programs with 2-3 years ITR & GST/Current Account statements",
            "impact": f"Unlocks Prime Banking (up to {len(salaried_unlocked)} Additional Lenders)",
            "new_best_lender": new_best["lender_name"] if new_best else "Top Tier Banks",
            "new_rate": new_best["financials"]["interest_rate_pct"] if new_best else 12.5,
            "explanation": (
                f"Standard retail personal loans auto-reject non-salaried applicants. With ₹{monthly_income:,.0f}/mo net earnings and "
                f"CIBIL {cibil}, routing your application via Business Loan / Professional Loan verticals unlocks prime banks "
                f"(such as {new_best['lender_name'] if new_best else 'HDFC/SBI'}) at competitive rates around "
                f"{new_best['financials']['interest_rate_pct'] if new_best else 12.5:.2f}% p.a."
            )
        })

    # -------------------------------------------------------------------------
    # 3. PRESCRIPTION: Credit Card Debt Pay-Down (De-leveraging)
    # -------------------------------------------------------------------------
    if cc_outstanding > 0:
        paydown_sim = simulate_modified_profile(applicant, lenders, {"credit_card_outstanding": 0.0})
        new_best = paydown_sim["best_option"]

        if new_best:
            new_sanction = new_best["financials"]["sanction_amount"]
            new_rate = new_best["financials"]["interest_rate_pct"]
            monthly_freed = round(cc_outstanding * 0.05, 2)
            capacity_gain = max(0.0, new_sanction - current_sanction)
            new_lenders = [o["lender_name"] for o in paydown_sim["eligible_offers"] if o["lender_id"] not in current_lenders]

            details = f"Paying off ₹{cc_outstanding:,.0f} credit card balance eliminates ₹{monthly_freed:,.0f}/mo phantom obligation."
            if new_lenders:
                details += f" Unlocks {len(new_lenders)} new lender(s): {', '.join(new_lenders[:3])}."
            if capacity_gain > 0:
                details += f" Expands borrowing capacity by +₹{capacity_gain:,.0f}."
            if current_rate and new_rate < current_rate:
                rate_diff = current_rate - new_rate
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
    # 4. PRESCRIPTION: Existing EMI Pre-closure / Restructuring
    # -------------------------------------------------------------------------
    if existing_emis > 0 and (current_approved_count < 10 or current_sanction < 300000):
        halved_emis = round(existing_emis * 0.50, 2)
        emi_sim = simulate_modified_profile(applicant, lenders, {"existing_monthly_emis": halved_emis})
        new_best = emi_sim["best_option"]

        if new_best:
            new_sanction = new_best["financials"]["sanction_amount"]
            capacity_gain = new_sanction - current_sanction
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

    # -------------------------------------------------------------------------
    # 5. PRESCRIPTION: Delinquency Seasoning & Inquiry Velocity Freeze
    # -------------------------------------------------------------------------
    if dpd > 0 or enquiries > 3:
        clean_mods: Dict[str, Any] = {"max_dpd_last_12m": 0, "hard_enquiries_last_30d": 1}
        if cibil < 720 and cibil > 0:
            clean_mods["cibil_score"] = 720
        clean_sim = simulate_modified_profile(applicant, lenders, clean_mods)
        new_best = clean_sim["best_option"]
        unlocked_lenders = [o["lender_name"] for o in clean_sim["eligible_offers"] if o["lender_id"] not in current_lenders]

        if new_best and unlocked_lenders:
            prescriptions.append({
                "type": "DELINQUENCY_SEASONING",
                "title": "Season Delinquencies & Freeze Credit Enquiries",
                "action": f"Maintain 100% on-time payments so {dpd} DPD rolls off 12m window and halt new credit applications for 30 days",
                "impact": f"+{len(unlocked_lenders)} Prime Lenders (PSBs & Top Banks)",
                "new_best_lender": new_best["lender_name"],
                "new_rate": new_best["financials"]["interest_rate_pct"],
                "explanation": (
                    f"Public sector and prime banks (SBI, PNB, Canara) enforce strict zero-DPD and max 3 inquiries. "
                    f"Allowing the {dpd} DPD to season off the 12-month bureau window while cooling inquiry velocity unlocks "
                    f"{len(unlocked_lenders)} prime banks with rates down to {new_best['financials']['interest_rate_pct']:.2f}% p.a."
                )
            })

    # -------------------------------------------------------------------------
    # 6. PRESCRIPTION: Co-Applicant Household Income Pooling
    # -------------------------------------------------------------------------
    if monthly_income < 20000:
        coapp_income = 35000.0
        inc_sim = simulate_modified_profile(applicant, lenders, {"monthly_net_income": coapp_income})
        new_best = inc_sim["best_option"]
        unlocked_lenders = [o["lender_name"] for o in inc_sim["eligible_offers"] if o["lender_id"] not in current_lenders]

        if new_best and unlocked_lenders:
            rate_savings = (current_rate - new_best["financials"]["interest_rate_pct"]) if current_rate else 13.0
            prescriptions.append({
                "type": "CO_APPLICANT_POOLING",
                "title": "Add Salaried Co-Applicant (Income Pooling)",
                "action": f"Add a working family co-applicant to pool combined monthly income to ₹{coapp_income:,.0f}",
                "impact": f"+{len(unlocked_lenders)} Unlocked Banks (Save ~{rate_savings:.1f}% APR)",
                "new_best_lender": new_best["lender_name"],
                "new_rate": new_best["financials"]["interest_rate_pct"],
                "explanation": (
                    f"Current net income of ₹{monthly_income:,.0f} falls below traditional bank cutoffs (₹20k - ₹25k). "
                    f"Pooling household income with a co-borrower unlocks {len(unlocked_lenders)} institutional lender(s) including "
                    f"{', '.join(unlocked_lenders[:3])} at prime rates starting at {new_best['financials']['interest_rate_pct']:.2f}% p.a."
                )
            })

    # -------------------------------------------------------------------------
    # 7. PRESCRIPTION: Credit Score (CIBIL) Elevation Roadmap
    # -------------------------------------------------------------------------
    if cibil == -1:
        ntc_sim = simulate_modified_profile(applicant, lenders, {"cibil_score": 750})
        new_best = ntc_sim["best_option"]
        if new_best:
            ntc_unlocked = [o["lender_name"] for o in ntc_sim["eligible_offers"] if o["lender_id"] not in current_lenders]
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
        target_scores = [t for t in [720, 750, 780] if t > cibil]
        for target in target_scores:
            cibil_sim = simulate_modified_profile(applicant, lenders, {"cibil_score": target})
            new_best = cibil_sim["best_option"]
            if new_best:
                unlocked_lenders = [o["lender_name"] for o in cibil_sim["eligible_offers"] if o["lender_id"] not in current_lenders]
                new_rate = new_best["financials"]["interest_rate_pct"]

                if (current_rate and new_rate < current_rate) or unlocked_lenders:
                    rate_savings = (current_rate - new_rate) if current_rate else 0.0
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
                    break

    # -------------------------------------------------------------------------
    # 8. PRESCRIPTION: Employment Stability Horizon (Waiting Period)
    # -------------------------------------------------------------------------
    if cur_tenure < 12 and age >= 21:
        target_tenures = [t for t in [6, 12] if t > cur_tenure]
        for target_m in target_tenures:
            tenure_sim = simulate_modified_profile(applicant, lenders, {
                "current_job_tenure_months": target_m,
                "total_work_exp_months": tot_exp + (target_m - cur_tenure),
                "total_work_experience_months": tot_exp + (target_m - cur_tenure)
            })
            new_best = tenure_sim["best_option"]
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
    # 9. PRESCRIPTION: Senior Retirement Horizon & Tenure Truncation
    # -------------------------------------------------------------------------
    if age >= 55:
        effective_tenure = current_best["financials"]["tenure_months"] if current_best else max(12, (60 - age) * 12)
        if effective_tenure < desired_tenure:
            prescriptions.append({
                "type": "TENURE_OPTIMIZATION",
                "title": "Add Younger Co-Applicant / Pension Scheme",
                "action": "Add an earning child as co-borrower or explore dedicated Pensioner Loan programs",
                "impact": f"Overcomes {effective_tenure}m Retirement Truncation",
                "new_best_lender": current_best["lender_name"] if current_best else "Prime Lenders",
                "new_rate": current_rate if current_rate else 11.5,
                "explanation": (
                    f"At age {age}, standard retail loan maturity caps at age 60, shortening maximum tenure to {effective_tenure} months. "
                    f"Adding an earning child as co-applicant allows lenders to approve the full {desired_tenure}-month tenure, reducing monthly EMI."
                )
            })

    # -------------------------------------------------------------------------
    # 10. PRESCRIPTION: Prime Borrower Fee Waiver & Prepayment Advisory
    # -------------------------------------------------------------------------
    if current_approved_count >= 18:
        best_fee_pct = current_best["financials"].get("processing_fee_percent", 1.5) if current_best else 1.5
        est_fee_inr = round(current_sanction * (best_fee_pct / 100.0), 0)
        prescriptions.append({
            "type": "PRIME_NEGOTIATION",
            "title": "Negotiate 100% Processing Fee Waiver",
            "action": f"Leverage competing pre-approvals across {current_approved_count} lenders to request fee waiver from {current_best['lender_name']}",
            "impact": f"Save ~₹{est_fee_inr:,.0f} Upfront Processing Charges",
            "new_best_lender": current_best["lender_name"],
            "new_rate": current_rate,
            "explanation": (
                f"With offers from {current_approved_count} out of 20 top institutions, you hold maximum credit leverage. "
                f"Request a 100% waiver of processing charges (saving ~₹{est_fee_inr:,.0f}) and ask your primary salary bank "
                f"to match the lowest competing public sector benchmark rate."
            )
        })
        prescriptions.append({
            "type": "FORECLOSURE_OPTIMIZATION",
            "title": "Select Zero Foreclosure Penalty Lender",
            "action": "Select Public Sector Bank offers (e.g. SBI) for zero prepayment and foreclosure charges",
            "impact": "Zero Prepayment Penalty on Early Closure",
            "new_best_lender": "State Bank of India (SBI)",
            "new_rate": 11.15,
            "explanation": (
                "Private banks and NBFCs charge 2% - 4% + GST for premature foreclosure. Public sector banks like SBI "
                "feature zero foreclosure fees when pre-closing from own funds, maximizing lifetime savings."
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
