"""
Personal Loan Eligibility Model - CLI Runner (Pure CSV Architecture)
--------------------------------------------------------------------
Main entry point for evaluating borrower eligibility, loan sizing,
and lender recommendations across 20 Indian financial institutions.
Operates exclusively with CSV data inputs and CSV exports.

Usage Examples:
    python main.py --test-all
    python main.py --profile-id PROFILE_01
    python main.py --interactive
    python main.py --profile-file path/to/custom_applicant.csv
"""

import sys
import os
import csv
import argparse
from typing import Dict, Any, List

# Ensure safe cross-platform UTF-8 terminal printing on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.rule_engine import load_lender_rules, load_applicant_profiles, underwrite_applicant_all_lenders
from src.ranker import get_recommendation_summary, format_underwriting_report


DEFAULT_LENDERS_PATH = os.path.join("data", "lender_rules.csv")
DEFAULT_PROFILES_PATH = os.path.join("data", "test_profiles.csv")
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_OUTPUT_CSV = os.path.join(DEFAULT_OUTPUT_DIR, "test_results.csv")


def ensure_output_dir_exists():
    """Ensure output directory is available for result exports."""
    if not os.path.exists(DEFAULT_OUTPUT_DIR):
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)


def run_single_profile(
    applicant: Dict[str, Any],
    lenders: List[Dict[str, Any]],
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Execute underwriting waterfall for a single applicant and return recommendations.

    Args:
        applicant: Applicant profile dictionary.
        lenders: List of lender policies.
        verbose: Whether to print the formatted report to stdout.

    Returns:
        Structured recommendation dictionary.
    """
    evaluations = underwrite_applicant_all_lenders(applicant, lenders)
    decision = get_recommendation_summary(evaluations)

    if verbose:
        report_str = format_underwriting_report(applicant, decision)
        print(report_str)

    return {
        "applicant": applicant,
        "decision": decision
    }


def export_test_results_to_csv(all_results: List[Dict[str, Any]], csv_path: str):
    """
    Export underwriting results for all test profiles to a pure CSV file.

    Args:
        all_results: List of execution results per applicant.
        csv_path: Destination CSV file path.
    """
    rows = []
    for res in all_results:
        app = res["applicant"]
        dec = res["decision"]
        best = dec.get("best_option")
        fin = best["financials"] if best else {}

        row = {
            "applicant_id": app.get("applicant_id", app.get("profile_id", "Unknown")),
            "name": app.get("name", "Unknown"),
            "age": app.get("age", 0),
            "employment_type": app.get("employment_type", ""),
            "employer_category": app.get("employer_category", ""),
            "monthly_net_income": app.get("monthly_net_income", 0.0),
            "existing_monthly_emis": app.get("existing_monthly_emis", 0.0),
            "credit_card_outstanding": app.get("credit_card_outstanding", 0.0),
            "cibil_score": app.get("cibil_score", -1),
            "city_tier": app.get("city_tier", ""),
            "total_lenders_evaluated": dec["summary"]["total_lenders_evaluated"],
            "approved_count": dec["summary"]["approved_count"],
            "rejected_count": dec["summary"]["rejected_count"],
            "approval_rate_percent": dec["summary"]["approval_rate_percent"],
            "best_recommended_lender": best["lender_name"] if best else "None (Rejected)",
            "best_institution_type": best["institution_type"] if best else "N/A",
            "best_sanction_amount": fin.get("sanction_amount", 0.0),
            "best_interest_rate_pct": fin.get("interest_rate_pct", 0.0),
            "best_tenure_months": fin.get("tenure_months", 0),
            "best_monthly_emi": fin.get("monthly_emi", 0.0),
            "best_total_interest": fin.get("total_interest", 0.0),
            "best_processing_fee_inr": fin.get("processing_fee_inr", 0.0),
            "best_total_cost_of_credit": fin.get("total_cost_of_credit", 0.0),
            "best_source_url": fin.get("source", "")
        }
        rows.append(row)

    if rows:
        fieldnames = list(rows[0].keys())
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def run_all_test_profiles(
    lenders_path: str = DEFAULT_LENDERS_PATH,
    profiles_path: str = DEFAULT_PROFILES_PATH,
    output_csv_path: str = DEFAULT_OUTPUT_CSV
) -> List[Dict[str, Any]]:
    """
    Execute underwriting pipeline for all benchmark test profiles
    and persist results strictly to CSV.

    Args:
        lenders_path: Path to lender policy CSV.
        profiles_path: Path to test profiles CSV.
        output_csv_path: Path to save tabular execution output CSV.

    Returns:
        List of results across all profiles.
    """
    ensure_output_dir_exists()
    lenders = load_lender_rules(lenders_path)
    profiles = load_applicant_profiles(profiles_path)

    print("\n" + "#" * 80)
    print(f"RUNNING UNDERWRITING WATERFALL ENGINE ACROSS {len(profiles)} BENCHMARK PROFILES (CSV ONLY)")
    print(f"Lender Rules Source : {lenders_path} ({len(lenders)} Lenders)")
    print(f"Profiles Source     : {profiles_path}")
    print("#" * 80 + "\n")

    all_results = []

    for profile in profiles:
        result = run_single_profile(profile, lenders, verbose=True)
        all_results.append(result)

    # Save tabular CSV output
    export_test_results_to_csv(all_results, output_csv_path)

    print(f"\n[SUCCESS] Completed evaluation of {len(profiles)} profiles.")
    print(f"[EXPORT] Tabular underwriting results exported strictly to: {output_csv_path}\n")

    return all_results


def interactive_mode(lenders_path: str = DEFAULT_LENDERS_PATH):
    """
    Interactive CLI wizard to underwrite an applicant entered dynamically.
    """
    lenders = load_lender_rules(lenders_path)
    print("\n" + "=" * 60)
    print("PERSONAL LOAN UNDERWRITING INTERACTIVE WIZARD")
    print("=" * 60)

    try:
        age_str = input("Enter Age in years [default: 28]: ").strip()
        age = int(age_str) if age_str else 28

        emp_type_str = input("Enter Employment Type (1: Salaried, 2: Self-Employed) [default: 1]: ").strip()
        employment_type = "Self-Employed" if emp_type_str == "2" else "Salaried"

        emp_cat_str = input("Employer Category (CAT-A, CAT-B, CAT-C, Government) [default: CAT-A]: ").strip().upper()
        employer_category = emp_cat_str if emp_cat_str in ["CAT-A", "CAT-B", "CAT-C", "GOVERNMENT"] else "CAT-A"

        tot_exp_str = input("Total Work Experience in months [default: 36]: ").strip()
        total_exp = int(tot_exp_str) if tot_exp_str else 36

        cur_exp_str = input("Current Job Tenure in months [default: 18]: ").strip()
        cur_exp = int(cur_exp_str) if cur_exp_str else 18

        income_str = input("Monthly Net In-Hand Income in INR [default: 75000]: ").strip()
        monthly_income = float(income_str) if income_str else 75000.0

        emis_str = input("Existing Monthly EMIs currently being paid in INR [default: 10000]: ").strip()
        existing_emis = float(emis_str) if emis_str else 10000.0

        cc_str = input("Total Credit Card Outstanding Balance in INR [default: 0]: ").strip()
        credit_card_outstanding = float(cc_str) if cc_str else 0.0

        cibil_str = input("CIBIL Score (300-900, or -1 for New-To-Credit) [default: 760]: ").strip()
        cibil = int(cibil_str) if cibil_str else 760

        city_str = input("City Tier (1: Metro, 2: Non-Metro / Tier 2, 3: Tier 1) [default: 1]: ").strip()
        city_mapping = {"1": "Metro", "2": "Non-Metro", "3": "Tier 1"}
        city_tier = city_mapping.get(city_str, "Metro")

        desired_amount_str = input("Desired Loan Amount in INR (or Press Enter for Max Eligible): ").strip()
        desired_loan = float(desired_amount_str) if desired_amount_str else None

        desired_tenure_str = input("Desired Loan Tenure in months (or Press Enter for Max Eligible): ").strip()
        desired_tenure = int(desired_tenure_str) if desired_tenure_str else None

        applicant = {
            "applicant_id": "INTERACTIVE_CUSTOM",
            "profile_id": "INTERACTIVE_CUSTOM",
            "name": "Interactive Applicant Profile",
            "age": age,
            "employment_type": employment_type,
            "employer_category": employer_category,
            "total_work_exp_months": total_exp,
            "total_work_experience_months": total_exp,
            "current_job_tenure_months": cur_exp,
            "monthly_net_income": monthly_income,
            "existing_monthly_emis": existing_emis,
            "credit_card_outstanding": credit_card_outstanding,
            "cibil_score": cibil,
            "city_tier": city_tier,
            "desired_loan_amount": desired_loan,
            "desired_tenure_months": desired_tenure
        }

        run_single_profile(applicant, lenders, verbose=True)

    except KeyboardInterrupt:
        print("\n\nInteractive evaluation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Invalid input provided: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic Underwriting Waterfall & Personal Loan Eligibility Model (CSV Only)"
    )
    parser.add_argument(
        "--test-all",
        action="store_true",
        help="Run underwriting pipeline on all benchmark test profiles and export to CSV."
    )
    parser.add_argument(
        "--profile-id",
        type=str,
        help="Run underwriting for a specific benchmark profile (e.g., PROFILE_01, PROFILE_05)."
    )
    parser.add_argument(
        "--profile-file",
        type=str,
        help="Path to an external CSV file containing custom applicant profile(s)."
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive terminal wizard for dynamic applicant input."
    )
    parser.add_argument(
        "--lenders-file",
        type=str,
        default=DEFAULT_LENDERS_PATH,
        help=f"Path to lender policies CSV (default: {DEFAULT_LENDERS_PATH})."
    )
    parser.add_argument(
        "--profiles-file",
        type=str,
        default=DEFAULT_PROFILES_PATH,
        help=f"Path to test profiles CSV (default: {DEFAULT_PROFILES_PATH})."
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=DEFAULT_OUTPUT_CSV,
        help=f"Path to output CSV destination (default: {DEFAULT_OUTPUT_CSV})."
    )

    args = parser.parse_args()

    if args.test_all:
        run_all_test_profiles(
            lenders_path=args.lenders_file,
            profiles_path=args.profiles_file,
            output_csv_path=args.output_csv
        )
    elif args.profile_id:
        profiles = load_applicant_profiles(args.profiles_file)
        target_id = args.profile_id.upper()
        matched = [
            p for p in profiles 
            if p.get("applicant_id", "").upper() == target_id or p.get("profile_id", "").upper() == target_id
        ]
        if not matched:
            print(f"[ERROR] Profile ID '{args.profile_id}' not found in {args.profiles_file}.")
            sys.exit(1)
        lenders = load_lender_rules(args.lenders_file)
        run_single_profile(matched[0], lenders, verbose=True)
    elif args.profile_file:
        profiles = load_applicant_profiles(args.profile_file)
        lenders = load_lender_rules(args.lenders_file)
        for p in profiles:
            run_single_profile(p, lenders, verbose=True)
    elif args.interactive:
        interactive_mode(args.lenders_file)
    else:
        print("No command flags specified. Executing default benchmark test suite across CSV profiles...")
        run_all_test_profiles(
            lenders_path=args.lenders_file,
            profiles_path=args.profiles_file,
            output_csv_path=args.output_csv
        )


if __name__ == "__main__":
    main()
