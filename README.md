# PLE-Birbal: Personal Loan Eligibility & Underwriting Engine

Deterministic credit underwriting engine and personal loan recommendation system covering 20 Indian banks and NBFCs (Public Sector Banks, Private Banks, and NBFCs). Evaluates borrower profiles across hard knockout rules, risk-based pricing, debt-burden capacity (FOIR), and generates actionable What-If improvement plans.

Accessible via web dashboard and CLI.

**Live Application:** [https://personal-loan-eligibility-birbal.onrender.com/](https://personal-loan-eligibility-birbal.onrender.com/)

---

## Architecture Overview

Credit underwriting in regulated financial institutions relies on explainable, deterministic rule sets rather than opaque black-box models. This project implements a 5-stage waterfall:

1. **Stage 1: Hard Knockout Rules**
   - Applicant age boundaries (21 to 58/60)
   - Employment classification (Salaried vs. Self-Employed)
   - City-tier minimum salary requirements (Metro, Tier 1, Non-Metro)
   - Total work experience and current job stability
   - Bureau delinquency criteria: 12-month Days Past Due (DPD) limits, 30-day hard inquiry velocity, zero active overdue tolerance, and write-offs

2. **Stage 2: Risk-Based Pricing**
   - Maps borrower CIBIL score to lender-specific pricing bands
   - Determines the applicable starting interest rate

3. **Stage 3: Debt Capacity & Loan Sizing**
   - Retirement-adjusted maximum loan tenure
   - Dynamic income-tiered Fixed Obligation to Income Ratio (FOIR)
   - 5% credit card balance load factor on revolving balances
   - Loan sizing via Present Value annuity of allowable EMI
   - Corporate employer category multiplier caps (CAT-A, CAT-B, CAT-C, Government)

4. **Stage 4: Ranking & Recommendation**
   - Filters eligible vs. ineligible lenders
   - Multi-criteria ranking: lowest interest rate, followed by total cost of credit
   - Detailed rejection reasons with audit rule IDs for ineligible institutions

5. **Stage 5: What-If Prescription Engine**
   - Simulates profile improvements to unlock better interest rates and higher loan limits
   - Evaluates credit card debt pay-down, CIBIL score elevation milestones, employment vintage milestones, delinquency seasoning, co-applicant income pooling, and business loan channels

---

## Lenders Configured

The engine configures credit policies for 20 financial institutions across three categories:

- **Public Sector Banks:** State Bank of India (SBI), Punjab National Bank (PNB), Bank of Baroda, Canara Bank
- **Private Sector Banks:** HDFC Bank, ICICI Bank, Axis Bank, Kotak Mahindra Bank, IndusInd Bank, IDFC FIRST Bank, Yes Bank
- **NBFCs & Fintechs:** Bajaj Finance, Tata Capital, Aditya Birla Capital, L&T Finance, Poonawalla Fincorp, Piramal Finance, Navi, MoneyTap / Freo, KreditBee

---

## Test Profiles

The system includes 10 test profiles covering common credit evaluation scenarios:

| Profile ID | Scenario | Key Factors | Test Objective |
|---|---|---|---|
| `PROFILE_01` | High Earner (New to Credit) | ₹1.5L salary, CIBIL -1 (NTC) | New-to-credit acceptance policy |
| `PROFILE_02` | Over-Leveraged Professional | CIBIL 780, ₹1.2L salary, ₹75k obligations | FOIR breach and credit card debt load |
| `PROFILE_03` | Credit-Impaired Applicant | ₹45k salary, CIBIL 610, 30 DPD, 4 inquiries | Delinquency limits and bureau knockouts |
| `PROFILE_04` | Job Hopper | 8m total experience, 1m current job | Job stability hurdles |
| `PROFILE_05` | Senior Near Retirement | Age 58, Government employee, CIBIL 760 | Tenure truncation to retirement age (60) |
| `PROFILE_06` | Young Fresh Graduate | Age 20, ₹35k salary | Minimum applicant age hurdle (21) |
| `PROFILE_07` | Minimum Wage Salaried Worker | ₹14k salary, Metro | Metro city minimum income hurdle |
| `PROFILE_08` | Self-Employed Consultant | ₹90k salary, Self-Employed | Salaried product restriction filter |
| `PROFILE_09` | Top-Tier Corporate Employee | ₹2.0L salary, CAT-A MNC, CIBIL 820 | Prime rate eligibility across all lenders |
| `PROFILE_10` | Boundary Case | Exactly age 21, ₹25k salary, CIBIL 700 | Exact policy cutoff validation |

---

## Project Structure

```
├── data/
│   ├── knockout_rules.csv         # Atomic knockout rules across all lenders
│   ├── lender_rules_matrix.csv    # Lender policy matrix, rate bands, and limits
│   ├── datapoints_schema.csv      # Data dictionary for applicant parameters
│   └── test_profiles.csv          # 10 benchmark test profiles
├── src/
│   ├── loan_calculator.py         # Financial calculations (EMI, FOIR, PV annuity)
│   ├── rule_engine.py             # Underwriting waterfall and policy evaluations
│   ├── ranker.py                  # Offer ranking and comparison logic
│   └── prescription_engine.py     # Counterfactual What-If simulation engine
├── web/
│   ├── index.html                 # Web dashboard interface
│   ├── css/style.css              # Dashboard styling
│   └── js/app.js                  # Frontend interactions and API calls
├── output/
│   └── test_results.csv           # Evaluation results export
├── main.py                        # CLI runner and interactive wizard
├── server.py                      # Local web server and REST API
├── requirements.txt               # Dependencies
└── Dockerfile                     # Container configuration
```

---

## Getting Started

### Prerequisites

- Python 3.9+

### Installation

```bash
# Clone the repository
git clone https://github.com/Prakshil/Personal-Loan-Eligibility-Underwriting-Waterfall-Engine.git
cd Personal-Loan-Eligibility-Underwriting-Waterfall-Engine

# Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### 1. Web Dashboard

Start the local server:
```bash
python server.py 5050
```
Open `http://localhost:5050` in your browser.

### 2. Command Line Interface

Run all 10 benchmark test profiles and export results to `output/test_results.csv`:
```bash
python main.py --test-all
```

Underwrite a specific test profile:
```bash
python main.py --profile-id PROFILE_01
python main.py --profile-id PROFILE_03
```

Interactive terminal wizard:
```bash
python main.py --interactive
```

Underwrite a custom applicant CSV:
```bash
python main.py --profile-file path/to/applicant.csv
```

---

## Docker Deployment

Build and run using Docker:

```bash
docker build -t ple-birbal .
docker run -p 5050:5050 ple-birbal
```

The application will be accessible at `http://localhost:5050`.
