# Personal Loan Eligibility & Underwriting Waterfall Engine

A deterministic, production-grade credit underwriting rule engine and loan recommendation system modeled after the Indian retail lending ecosystem (covering Public Sector Banks, Private Sector Banks, NBFCs, and Fintech lenders).

---

## 1. Problem Statement & Architecture

In retail lending, when labeled historical approval/rejection data is unavailable (or regulatory compliance prevents opaque "black-box" decisions), machine learning classifiers are strictly prohibited. Credit underwriting in regulated institutions (RBI-regulated banks and NBFCs) relies on **deterministic rule engines** and **waterfall decision trees**. Every loan decision must be explainable, defensible, and auditable.

This repository implements a **4-stage Underwriting Waterfall**:

```
             [Applicant Profile]
                      │
                      ▼
┌───────────────────────────────────────────┐
│  Stage 1: Hard Knockout Rules Filter      │
│  - Age (21-58/60)                         │
│  - Employment Type (Salaried / SE)        │
│  - City-Tier Minimum Income Check         │
│  - CIBIL Bureau Threshold & NTC Acceptance│
│  - Total & Current Employer Tenure        │
│  - Initial FOIR Debt-Burden Feasibility   │
└─────────────────────┬─────────────────────┘
                      │ Pass / Fail per Lender
                      │ (Explicit Rejection Reasons)
                      ▼
┌───────────────────────────────────────────┐
│  Stage 2: Risk-Based Pricing Engine       │
│  - Map CIBIL score to Lender Rate Bands   │
│  - Resolve applicable base / risk spread  │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│  Stage 3: Debt Capacity & Sizing Engine   │
│  - Retirement-adjusted Maximum Tenure     │
│  - Surplus EMI Capacity via FOIR          │
│  - Annuity Capitalization (PV of EMI)     │
│  - Gross Salary Multiplier Cap            │
│  - Prudent Sanction Amount Determination  │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│  Stage 4: Recommendation & Ranking Engine │
│  - Filter Eligible vs Ineligible          │
│  - Multi-Criteria Sorting (APR > Cost)    │
│  - Designate #1 "Best Recommended Option" │
│  - Generate Granular Audit Trails         │
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


### 2.2 Age-Adjusted Maximum Tenure (Retirement Cutoff)
Personal loans are unsecured credit; repayment cannot extend into unverified post-retirement years.
$$\text{Months to Retirement} = (\text{Lender Max Age} - \text{Applicant Age}) \times 12$$
$$\text{Effective Max Tenure} = \min(\text{Lender Policy Max Tenure}, \text{Months to Retirement})$$

*If $\text{Effective Max Tenure} < \text{Lender Min Tenure}$, the applicant is rejected.*

### 2.3 Maximum Loan Capacity via Annuity (Present Value of EMI)
Using the monthly compound interest rate $r = \frac{\text{Annual Interest Rate}}{12 \times 100}$ and tenure $n$ months:

$$\text{Max Loan}_{\text{FOIR}} = \text{Max Allowed EMI} \times \left[ \frac{1 - (1 + r)^{-n}}{r} \right]$$

### 2.4 Maximum Loan via Employer Category Salary Multiplier
Lenders enforce an absolute policy cap based on monthly income and corporate risk tiering:
- **CAT-A (MNC / Fortune 500):** Prime multiplier of 20x to 24x monthly salary.
- **Government / PSU:** 18x to 22x monthly salary.
- **CAT-B (Mid Corporates):** 16x to 18x monthly salary.
- **CAT-C (Unlisted / MSME):** Conservative multiplier of 12x to 15x monthly salary.

$$\text{Max Loan}_{\text{Multiplier}} = \text{Monthly Net Income} \times \text{Employer Tier Multiplier}$$


### 2.5 Eligible Sanction Amount
The final loan sanction is capped by the most conservative constraint and rounded down to standard banking denominations (nearest ₹1,000):

$$\text{Sanction Amount} = \min(\text{Max Loan}_{\text{FOIR}}, \text{Max Loan}_{\text{Multiplier}}, \text{Lender Max Limit}, \text{Desired Loan})$$

$$\text{EMI} = P \times r \times \frac{(1 + r)^n}{(1 + r)^n - 1}$$

---

## 3. Top 20 Indian Lenders Configured

The engine includes 20 institutional lenders across three standard risk and operating categories:

1. **Public Sector Banks (PSBs):** State Bank of India (SBI), Punjab National Bank (PNB), Bank of Baroda, Canara Bank.
   - *Profile:* Conservative risk appetite, strict CIBIL hurdles (≥720), lower interest rates (11.15%–12.85%), longer job stability requirements (≥12 months current job).
2. **Private Sector Banks:** HDFC Bank, ICICI Bank, Axis Bank, Kotak Mahindra Bank, IndusInd Bank, IDFC FIRST Bank, Yes Bank.
   - *Profile:* Balanced risk appetite, competitive prime rates (10.75%–13.50%), fast turnaround, moderate CIBIL hurdles (≥700–720).
3. **NBFCs & Fintechs:** Bajaj Finance, Tata Capital, Aditya Birla Capital, L&T Finance, Poonawalla Fincorp, Piramal Finance, Navi, MoneyTap/Freo, KreditBee.
   - *Profile:* Higher risk appetite, wider eligibility (CIBIL down to 600 or NTC / -1), higher FOIR limits (up to 65%), higher interest rate bands (14%–28.5%).

---

## 4. Benchmark Test Suite: 10 Edge-Case Profiles

| Profile ID | Profile Name | Key Underwriting Attribute | Primary Stress Tested |
|---|---|---|---|
| `PROFILE_01` | The Thin-File / High-Earner | ₹1.5L salary, `CIBIL = -1` (NTC) | New-To-Credit acceptance policy |
| `PROFILE_02` | The Over-Leveraged Professional | CIBIL 780, ₹1.2L salary, ₹75k existing EMIs | Hard FOIR breach (>60%) |
| `PROFILE_03` | The Credit-Impaired Applicant | ₹45k salary, CIBIL 610 | Sub-prime bureau cutoff |
| `PROFILE_04` | The Job Hopper | 8m total exp, 1m current job | Employment stability criteria |
| `PROFILE_05` | The Senior Near Retirement | Age 58, Govt employee, CIBIL 760 | Tenure truncation to 24 months |
| `PROFILE_06` | The Young Fresh Graduate | Age 20, ₹35k salary | Minimum applicant age cutoff (21) |
| `PROFILE_07` | The Minimum Wage Salaried Worker | ₹14k salary, Metro | Metro income hurdle (₹20k–₹25k) |
| `PROFILE_08` | The Gig / Contract / Self-Employed | ₹90k salary, Self-Employed | Salaried product restriction |
| `PROFILE_09` | The Top-Tier Corporate Employee | ₹2.0L salary, CAT-A MNC, CIBIL 820 | Prime rate eligibility across all 20 |
| `PROFILE_10` | The Boundary Case | Exactly age 21, ₹25k salary, CIBIL 700 | Exact boundary condition validation |

---

## 5. Key Industry Insights & Empirical Findings

1. **Most Frequent Failure Point:**
   - Credit score threshold (<700) accounts for over **65% of institutional rejections** among traditional banks.
   - FOIR breaches (>50%) represent the second largest knockout cause, particularly among urban middle-income borrowers servicing existing personal or auto loans.
2. **Lender Risk Appetite Divergence:**
   - Tier-1 Private Banks and PSBs strictly avoid New-To-Credit (NTC) unsecured personal loans unless backed by an existing salary account relationship.
   - In contrast, Fintech NBFCs (Navi, KreditBee) leverage proprietary alternative risk scoring to accept NTC applicants at risk-adjusted interest rates (21%–28.5%).
3. **Public Calculator vs. Underwriting Policy Discrepancy:**
   - Public-facing marketing calculators typically assume an unconstrained 50% FOIR and 60-month maximum tenure.
   - In actual credit policy sheets, effective tenure is strictly constrained by retirement age, FOIR scales dynamically from 40% (for incomes <₹25k) to 65% (for incomes >₹1.5L), and salary multipliers cap the maximum sanctioned principal.

---

## 6. Directory Structure (Hybrid Enterprise CSV Architecture)

```
personal-loan-eligibility-model/
├── data/
│   ├── knockout_rules.csv         # 520 atomic underwriting knockout rules (rule_id audit matrix)
│   ├── lender_rules_matrix.csv    # 20 lenders: 24 columns, rates, limits, unlisted methods, URLs
│   ├── datapoints_schema.csv      # Underwriting data dictionary, types, and sources
│   ├── lender_rules.csv           # Policy tables, slabs, and multipliers
│   └── test_profiles.csv          # 10 benchmark edge-case borrower profiles (CSV)
├── src/
│   ├── __init__.py                # Package initialization
│   ├── loan_calculator.py         # Financial math (FOIR, Annuity, EMI, Multipliers)
│   ├── rule_engine.py             # Hybrid waterfall engine: atomic knockouts & sizing
│   ├── ranker.py                  # Multi-criteria optimization, audit trail & report generator
│   └── prescription_engine.py     # What-If counterfactual sensitivity & prescription engine
├── output/
│   └── test_results.csv           # Tabular underwriting evaluation summary (CSV)
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
# 1. Run all 10 benchmark test profiles and export to output/test_results.csv
python main.py --test-all

# 2. Run a specific test profile
python main.py --profile-id PROFILE_01
python main.py --profile-id PROFILE_05

# 3. Launch interactive underwriting wizard
python main.py --interactive

# 4. Underwrite a custom CSV applicant file
python main.py --profile-file path/to/applicant.csv
```
