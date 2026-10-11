# PLE-Birbal: Personal Loan Eligibility & Underwriting Engine

A deterministic, production-grade credit underwriting rule engine and loan recommendation system modeled after the Indian retail lending ecosystem (covering 20 Public Sector Banks, Private Sector Banks, NBFCs, and Fintech lenders). Accessible via an interactive modern web dashboard or a robust CLI.

---

## 1. Problem Statement & Architecture

In retail lending, when labeled historical approval/rejection data is unavailable (or regulatory compliance prevents opaque "black-box" decisions), machine learning classifiers are strictly prohibited. Credit underwriting in regulated institutions (RBI-regulated banks and NBFCs) relies on **deterministic rule engines** and **waterfall decision trees**. Every loan decision must be explainable, defensible, and auditable.

This repository implements a **5-stage Underwriting Waterfall**:

```
             [Applicant Profile]
                      │
                      ▼
┌───────────────────────────────────────────┐
│  Stage 1: Hard Knockout Rules Filter      │
│  - Age (21-58/60)                         │
│  - Employment Type (Salaried / SE)        │
│  - City-Tier Minimum Income Check         │
│  - Total & Current Employer Tenure        │
│  - Initial FOIR Debt-Burden Feasibility   │
│  - CIR / Bureau Credit Assessment:        │
│    • CIBIL Score Cutoffs & NTC Policy     │
│    • 12-Month DPD (Days Past Due) Delinq. │
│    • 30-Day Hard Credit Inquiry Velocity  │
│    • Active Overdue Balances & Write-Offs │
└─────────────────────┬─────────────────────┘
                      │ Pass / Fail per Lender
                      │ (Explicit [rule_id] Audit Logs)
                      ▼
┌───────────────────────────────────────────┐
│  Stage 2: Risk-Based Pricing Engine       │
│  - Map CIBIL score to Lender Rate Bands   │
│  - Continuous Risk-Adjusted APR Spreads   │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│  Stage 3: Debt Capacity & Sizing Engine   │
│  - Retirement-adjusted Maximum Tenure     │
│  - Income-Tiered Dynamic FOIR (40%-65%)   │
│  - 5% Credit Card Obligation Load         │
│  - Annuity Capitalization (PV of EMI)     │
│  - Corporate Tier Salary Multiplier Cap   │
│  - Prudent Sanction Amount Determination  │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│  Stage 4: Recommendation & Ranking Engine │
│  - Filter Eligible vs Ineligible          │
│  - Multi-Criteria Sorting (APR > Cost)    │
│  - Designate #1 "Best Recommended Option" │
│  - Granular Audit Trail & Policy Summary  │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│  Stage 5: What-If Prescription Engine     │
│  - De-leveraging Sensitivity Simulation   │
│  - CIBIL Elevation Target Milestones      │
│  - Employer Tenure Horizon Analysis       │
│  - Actionable Borrower Roadmap Generation │
└───────────────────────────────────────────┘
```

---

## 2. Mathematical Framework & Underwriting Formulas

### 2.1 Available Monthly EMI Capacity (Dynamic FOIR & Credit Card Factor)
Fixed Obligation to Income Ratio (FOIR) dictates the maximum percentage of an applicant's net salary that can be earmarked towards debt repayment across all institutional loans.

In real-world retail banking, this is calculated dynamically using **Income-Tiered FOIR Slabs** (e.g. 40% for entry salaries $\le$ ₹25,000 up to 60%–65% for high earners) and includes a **5% credit card load factor** on active credit card balances:

$$\text{Effective Monthly Obligations} = \text{Existing EMIs} + (\text{Credit Card Outstanding} \times 0.05)$$

$$\text{Max Allowed EMI} = (\text{Monthly Net Income} \times \text{Dynamic Lender FOIR}) - \text{Effective Monthly Obligations}$$

*If $\text{Max Allowed EMI} \le 0$, the applicant is rejected due to excessive debt leverage.*


### 2.2 CIR (Credit Information Report) & DPD (Days Past Due) Delinquency Framework
Institutional lenders inspect past repayment track records, credit-hunger velocity, and overdue balances:
1. **12-Month Historical Delinquency (`max_dpd_last_12m`):**
   - Public Sector Banks enforce **0 DPD** (zero tolerance for late payments).
   - Private Banks & Tier-1 NBFCs tolerate up to **30 DPD**.
   - Subprime Fintech NBFCs tolerate up to **60–90 DPD**.
2. **Credit-Hunger Velocity (`hard_enquiries_last_30d`):**
   - High hard inquiries indicate desperate credit seeking. PSBs cap inquiries at **$\le 3$ in 30 days**; Private banks allow $\le 4-5$; Fintech NBFCs allow up to $\le 6-8$.
3. **Active Overdue Balances (`active_overdue_inr`):**
   - Unresolved defaults ($\text{overdue} > 0$) or written-off accounts are auto-knockouts across all 20 institutions.


### 2.3 Age-Adjusted Maximum Tenure (Retirement Cutoff)
Personal loans are unsecured credit; repayment cannot extend into unverified post-retirement years.
$$\text{Months to Retirement} = (\text{Lender Max Age} - \text{Applicant Age}) \times 12$$
$$\text{Effective Max Tenure} = \min(\text{Lender Policy Max Tenure}, \text{Months to Retirement})$$

*If $\text{Effective Max Tenure} < \text{Lender Min Tenure}$, the applicant is rejected.*

### 2.4 Maximum Loan Capacity via Annuity (Present Value of EMI)
Using the monthly compound interest rate $r = \frac{\text{Annual Interest Rate}}{12 \times 100}$ and tenure $n$ months:

$$\text{Max Loan}_{\text{FOIR}} = \text{Max Allowed EMI} \times \left[ \frac{1 - (1 + r)^{-n}}{r} \right]$$

### 2.5 Maximum Loan via Employer Category Salary Multiplier
Lenders enforce an absolute policy cap based on monthly income and corporate risk tiering:
- **CAT-A (MNC / Fortune 500):** Prime multiplier of 20x to 24x monthly salary.
- **Government / PSU:** 18x to 22x monthly salary.
- **CAT-B (Mid Corporates):** 16x to 18x monthly salary.
- **CAT-C (Unlisted / MSME):** Conservative multiplier of 12x to 15x monthly salary.

$$\text{Max Loan}_{\text{Multiplier}} = \text{Monthly Net Income} \times \text{Employer Tier Multiplier}$$


### 2.6 Eligible Sanction Amount
The final loan sanction is capped by the most conservative constraint and rounded down to standard banking denominations (nearest ₹1,000):

$$\text{Sanction Amount} = \min(\text{Max Loan}_{\text{FOIR}}, \text{Max Loan}_{\text{Multiplier}}, \text{Lender Max Limit}, \text{Desired Loan})$$

$$\text{EMI} = P \times r \times \frac{(1 + r)^n}{(1 + r)^n - 1}$$

---

## 3. Top 20 Indian Lenders Configured

The engine includes 20 institutional lenders across three standard risk and operating categories:

1. **Public Sector Banks (PSBs):** State Bank of India (SBI), Punjab National Bank (PNB), Bank of Baroda, Canara Bank.
   - *Profile:* Conservative risk appetite, strict CIBIL hurdles (≥720), 0 DPD in 12m, $\le 3$ inquiries, lower interest rates (11.15%–12.85%), longer job stability requirements (≥12 months current job).
2. **Private Sector Banks:** HDFC Bank, ICICI Bank, Axis Bank, Kotak Mahindra Bank, IndusInd Bank, IDFC FIRST Bank, Yes Bank.
   - *Profile:* Balanced risk appetite, competitive prime rates (10.75%–13.50%), fast turnaround, moderate CIBIL hurdles (≥700–720), max 30 DPD.
3. **NBFCs & Fintechs:** Bajaj Finance, Tata Capital, Aditya Birla Capital, L&T Finance, Poonawalla Fincorp, Piramal Finance, Navi, MoneyTap/Freo, KreditBee.
   - *Profile:* Higher risk appetite, wider eligibility (CIBIL down to 600 or NTC / -1, DPD up to 60–90), higher FOIR limits (up to 65%), higher interest rate bands (14%–28.5%).

---

## 4. Benchmark Test Suite: 10 Edge-Case Profiles

| Profile ID | Profile Name | Key Underwriting Attribute | Primary Stress Tested |
|---|---|---|---|
| `PROFILE_01` | The Thin-File / High-Earner | ₹1.5L salary, `CIBIL = -1` (NTC), 0 DPD | New-To-Credit acceptance policy |
| `PROFILE_02` | The Over-Leveraged Professional | CIBIL 780, ₹1.2L salary, ₹75k existing EMIs + ₹2L CC | Hard FOIR breach & Credit Card loading |
| `PROFILE_03` | The Credit-Impaired Applicant | ₹45k salary, CIBIL 610, 30 DPD, 4 inquiries | Delinquency hurdles & sub-prime cutoff |
| `PROFILE_04` | The Job Hopper | 8m total exp, 1m current job | Employment stability criteria |
| `PROFILE_05` | The Senior Near Retirement | Age 58, Govt employee, CIBIL 760 | Tenure truncation to 24 months |
| `PROFILE_06` | The Young Fresh Graduate | Age 20, ₹35k salary | Minimum applicant age cutoff (21) |
| `PROFILE_07` | The Minimum Wage Salaried Worker | ₹14k salary, Metro | Metro income hurdle (₹20k–₹25k) |
| `PROFILE_08` | The Gig / Contract / Self-Employed | ₹90k salary, Self-Employed | Salaried product restriction |
| `PROFILE_09` | The Top-Tier Corporate Employee | ₹2.0L salary, CAT-A MNC, CIBIL 820, 0 DPD | Prime rate eligibility across all 20 |
| `PROFILE_10` | The Boundary Case | Exactly age 21, ₹25k salary, CIBIL 700 | Exact boundary condition validation |

---

## 5. Directory Structure (Hybrid Enterprise CSV Architecture)

```
personal-loan-eligibility-model/
├── data/
│   ├── knockout_rules.csv         # 600 atomic underwriting knockout rules (30 rules x 20 lenders)
│   ├── lender_rules_matrix.csv    # 20 lenders: 24 columns, rates, limits, unlisted methods, URLs
│   ├── datapoints_schema.csv      # Underwriting data dictionary (15 attributes)
│   ├── lender_rules.csv           # Policy tables, slabs, and multipliers
│   └── test_profiles.csv          # 10 benchmark edge-case borrower profiles (CSV)
├── src/
│   ├── __init__.py                # Package initialization
│   ├── loan_calculator.py         # Financial math (FOIR, Annuity, EMI, Multipliers)
│   ├── rule_engine.py             # Hybrid waterfall engine: 600 atomic knockouts & sizing
│   ├── ranker.py                  # Multi-criteria optimization, CIR/DPD audit trail & report
│   └── prescription_engine.py     # What-If counterfactual sensitivity & prescription engine
├── output/
│   └── test_results.csv           # Tabular underwriting evaluation summary (CSV)
├── web/                           # Modern Fable-inspired dark fintech web dashboard
│   ├── index.html                 # Semantic HTML5 dashboard & interactive telemetry form
│   ├── css/style.css              # Tokens-first vanilla CSS (glassmorphism & dark canvas)
│   └── js/app.js                  # Client application, preset loader & ranking renderer
├── server.py                      # Zero-dependency local HTTP server & REST API
├── main.py                        # Production CLI runner & interactive terminal wizard
├── requirements.txt               # Dependencies (pandas, tabulate)
└── README.md                      # Architecture documentation & underwriting guide
```

---

## 7. How to Run

### Setup Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Execution Commands
```bash
# 1. Launch the interactive web dashboard (Recommended)
python server.py
# Or via main CLI:
python main.py --serve --port 5050

# 2. Run all 10 benchmark test profiles and export to output/test_results.csv
python main.py --test-all

# 3. Run a specific test profile
python main.py --profile-id PROFILE_01
python main.py --profile-id PROFILE_05

# 4. Launch interactive terminal wizard
python main.py --interactive

# 5. Underwrite a custom CSV applicant file
python main.py --profile-file path/to/applicant.csv
```

---

## 8. Production Deployment Guide

PLE-Birbal is zero-dependency (built using pure Python standard library `http.server` with pure CSV data engines). It can be deployed in multiple production environments:

### Option A: Cloud Run / Render / Railway / Docker
Create a simple `Dockerfile` in the root:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5050
ENV PORT=5050
CMD ["python", "server.py", "5050"]
```
Deploy via CLI:
```bash
# Google Cloud Run
gcloud run deploy ple-birbal --source . --port 5050 --allow-unauthenticated

# Or Render / Railway
# Simply link the GitHub repository and specify Start Command: python server.py 5050
```

### Option B: Linux VPS (Ubuntu / Debian with systemd & Nginx)
1. **systemd service** (`/etc/systemd/system/ple-birbal.service`):
```ini
[Unit]
Description=PLE-Birbal Personal Loan Engine
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/PLE_Birbal
ExecStart=/var/www/PLE_Birbal/.venv/bin/python server.py 5050
Restart=always

[Install]
WantedBy=multi-user.target
```
2. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ple-birbal
```
3. Reverse proxy with Nginx:
```nginx
server {
    server_name loanengine.yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

