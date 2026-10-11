"""
Personal Loan Eligibility Underwriting Engine - Local Web Server
-----------------------------------------------------------------
Lightweight, zero-dependency HTTP server using Python's standard library.
Serves the modern Fable-styled dark fintech dashboard and exposes the
deterministic underwriting waterfall engine via REST endpoints.

Endpoints:
    GET  /                  -> Serves web/index.html
    GET  /api/profiles      -> Returns 10 benchmark test profiles
    GET  /api/lenders       -> Returns 20 institutional lenders
    POST /api/underwrite    -> Executes full waterfall underwriting, ranking & prescriptions
"""

import os
import sys
import json
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.rule_engine import (
    load_lender_rules,
    load_applicant_profiles,
    underwrite_applicant_all_lenders,
    DEFAULT_LENDER_MATRIX_PATH,
    DEFAULT_KNOCKOUT_RULES_PATH
)
from src.ranker import get_recommendation_summary
from src.prescription_engine import generate_what_if_prescriptions

PORT = 5050
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# Preload static engine data
LENDERS = load_lender_rules(DEFAULT_LENDER_MATRIX_PATH)
PROFILES_PATH = os.path.join("data", "test_profiles.csv")
PROFILES = load_applicant_profiles(PROFILES_PATH) if os.path.exists(PROFILES_PATH) else []


class UnderwritingRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving dashboard static assets and underwriting API."""

    def log_message(self, format, *args):
        # Concise server logging
        sys.stdout.write(f"[HTTP] {self.command} {self.path} - {args[1]}\n")

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_path = self.path.split("?")[0]

        if parsed_path == "/api/profiles":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(PROFILES, ensure_ascii=False).encode("utf-8"))
            return

        if parsed_path == "/api/lenders":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            summary_lenders = [
                {
                    "lender_id": l["lender_id"],
                    "lender_name": l["lender_name"],
                    "institution_type": l.get("institution_type", "Bank"),
                    "min_age": l["min_age"],
                    "max_age_application": l["max_age_application"],
                    "min_salary": l["min_salary"],
                    "min_cibil": l["min_cibil"],
                    "starting_rate": l["starting_interest_rate_pct"],
                    "ceiling_rate": l["ceiling_interest_rate_pct"],
                    "foir_cap": l.get("foir_cap_pct", 55.0),
                    "source": l.get("source", "")
                }
                for l in LENDERS
            ]
            self.wfile.write(json.dumps(summary_lenders, ensure_ascii=False).encode("utf-8"))
            return

        # Static file handling
        req_file = parsed_path.lstrip("/")
        if not req_file or req_file == "/":
            req_file = "index.html"

        file_path = os.path.join(WEB_DIR, req_file)

        # Normalize and prevent directory traversal
        file_path = os.path.abspath(file_path)
        if not file_path.startswith(os.path.abspath(WEB_DIR)):
            self.send_error(403, "Forbidden")
            return

        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_cors_headers()
            self.end_headers()

            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed_path = self.path.split("?")[0]

        if parsed_path == "/api/underwrite":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)

            try:
                applicant_data = json.loads(post_body.decode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Malformed JSON: {str(e)}")
                return

            # Clean and cast input data
            try:
                applicant = self._normalize_applicant_payload(applicant_data)
                evaluations = underwrite_applicant_all_lenders(applicant, LENDERS)
                decision = get_recommendation_summary(evaluations)
                prescriptions = generate_what_if_prescriptions(applicant, LENDERS, decision)

                response_payload = {
                    "status": "success",
                    "applicant": applicant,
                    "decision": decision,
                    "prescriptions": prescriptions
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(response_payload, ensure_ascii=False).encode("utf-8"))

            except Exception as err:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors_headers()
                self.end_headers()
                error_resp = {"status": "error", "message": str(err)}
                self.wfile.write(json.dumps(error_resp).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

    def _normalize_applicant_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize applicant payload to strict underwriting types."""
        desired_loan = data.get("desired_loan_amount")
        desired_tenure = data.get("desired_tenure_months")

        return {
            "applicant_id": str(data.get("applicant_id", "CUSTOM_APP")),
            "profile_id": str(data.get("profile_id", "CUSTOM_APP")),
            "name": str(data.get("name", "Custom Applicant")),
            "description": str(data.get("description", "Direct web evaluation")),
            "age": int(data.get("age", 30)),
            "employment_type": str(data.get("employment_type", "Salaried")),
            "employer_category": str(data.get("employer_category", "CAT_B")),
            "total_work_exp_months": int(data.get("total_work_exp_months", 24)),
            "total_work_experience_months": int(data.get("total_work_exp_months", 24)),
            "current_job_tenure_months": int(data.get("current_job_tenure_months", 12)),
            "monthly_net_income": float(data.get("monthly_net_income", 50000.0)),
            "existing_monthly_emis": float(data.get("existing_monthly_emis", 0.0)),
            "credit_card_outstanding": float(data.get("credit_card_outstanding", 0.0)),
            "cibil_score": int(data.get("cibil_score", 750)),
            "max_dpd_last_12m": int(data.get("max_dpd_last_12m", 0)),
            "hard_enquiries_last_30d": int(data.get("hard_enquiries_last_30d", 0)),
            "active_overdue_inr": float(data.get("active_overdue_inr", 0.0)),
            "written_off_accounts_count": int(data.get("written_off_accounts_count", 0)),
            "city_tier": str(data.get("city_tier", "Metro")),
            "desired_loan_amount": float(desired_loan) if desired_loan not in (None, "") else None,
            "desired_tenure_months": int(desired_tenure) if desired_tenure not in (None, "") else None
        }


def run_server(port: int = PORT, host: str = "0.0.0.0"):
    """Start local underwriting HTTP server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, UnderwritingRequestHandler)
    print("=" * 70)
    print(f"⚡ PLE-Birbal Underwriting Web Dashboard Live")
    print(f"👉 Local URL   : http://localhost:{port}")
    print(f"👉 Network URL : http://{host}:{port}")
    print(f"📋 Loaded      : {len(LENDERS)} Lenders | {len(PROFILES)} Test Profiles")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Underwriting server stopped.")
        httpd.server_close()


if __name__ == "__main__":
    # Prioritize command line arg, then PORT env var (used by Docker/Cloud), then default 5050
    port_to_use = int(os.environ.get("PORT", PORT))
    if len(sys.argv) > 1:
        try:
            port_to_use = int(sys.argv[1])
        except ValueError:
            pass
    host_to_use = os.environ.get("HOST", "0.0.0.0")
    run_server(port=port_to_use, host=host_to_use)
