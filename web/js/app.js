/**
 * PLE-Birbal // Personal Loan Eligibility & Bank Recommendation Engine
 * Client-Side Application Logic
 * - Sidebar Profile Selector
 * - Form Validation & Telemetry
 * - Deterministic API Client
 * - Zero Browser Alerts & Uncaught Errors
 */

// Default Fallback Benchmark Profiles (used if server is temporarily restarting)
const FALLBACK_PROFILES = [
  {
    applicant_id: "PROFILE_01",
    name: "High Earner (New to Credit)",
    age: 28,
    city_tier: "Metro",
    employment_type: "Salaried",
    employer_category: "CAT_A",
    total_work_exp_months: 36,
    current_job_tenure_months: 18,
    monthly_net_income: 150000,
    existing_monthly_emis: 0,
    credit_card_outstanding: 0,
    cibil_score: -1,
    max_dpd_last_12m: 0,
    hard_enquiries_last_30d: 1,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 500000,
    desired_tenure_months: 36
  },
  {
    applicant_id: "PROFILE_02",
    name: "Over-Leveraged (High EMIs & Cards)",
    age: 35,
    city_tier: "Metro",
    employment_type: "Salaried",
    employer_category: "CAT_A",
    total_work_exp_months: 84,
    current_job_tenure_months: 24,
    monthly_net_income: 120000,
    existing_monthly_emis: 65000,
    credit_card_outstanding: 200000,
    cibil_score: 780,
    max_dpd_last_12m: 0,
    hard_enquiries_last_30d: 3,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 300000,
    desired_tenure_months: 36
  },
  {
    applicant_id: "PROFILE_03",
    name: "Credit Impaired (30 Days Past Due)",
    age: 32,
    city_tier: "Tier 1",
    employment_type: "Salaried",
    employer_category: "CAT_B",
    total_work_exp_months: 48,
    current_job_tenure_months: 18,
    monthly_net_income: 45000,
    existing_monthly_emis: 5000,
    credit_card_outstanding: 0,
    cibil_score: 610,
    max_dpd_last_12m: 30,
    hard_enquiries_last_30d: 4,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 200000,
    desired_tenure_months: 24
  },
  {
    applicant_id: "PROFILE_04",
    name: "New at Current Company (1 Month)",
    age: 24,
    city_tier: "Metro",
    employment_type: "Salaried",
    employer_category: "CAT_B",
    total_work_exp_months: 8,
    current_job_tenure_months: 1,
    monthly_net_income: 40000,
    existing_monthly_emis: 0,
    credit_card_outstanding: 0,
    cibil_score: 740,
    max_dpd_last_12m: 0,
    hard_enquiries_last_30d: 2,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 100000,
    desired_tenure_months: 12
  },
  {
    applicant_id: "PROFILE_05",
    name: "Age 58 Govt Employee (Near Retirement)",
    age: 58,
    city_tier: "Tier 1",
    employment_type: "Salaried",
    employer_category: "GOVERNMENT",
    total_work_exp_months: 360,
    current_job_tenure_months: 120,
    monthly_net_income: 80000,
    existing_monthly_emis: 10000,
    credit_card_outstanding: 0,
    cibil_score: 760,
    max_dpd_last_12m: 0,
    hard_enquiries_last_30d: 0,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 500000,
    desired_tenure_months: 48
  },
  {
    applicant_id: "PROFILE_06",
    name: "Young Graduate (Age 20)",
    age: 20,
    city_tier: "Metro",
    employment_type: "Salaried",
    employer_category: "CAT_A",
    total_work_exp_months: 12,
    current_job_tenure_months: 6,
    monthly_net_income: 35000,
    existing_monthly_emis: 0,
    credit_card_outstanding: 0,
    cibil_score: 710,
    max_dpd_last_12m: 0,
    hard_enquiries_last_30d: 1,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 100000,
    desired_tenure_months: 12
  },
  {
    applicant_id: "PROFILE_07",
    name: "Entry Salary Worker",
    age: 26,
    city_tier: "Metro",
    employment_type: "Salaried",
    employer_category: "CAT_C",
    total_work_exp_months: 24,
    current_job_tenure_months: 12,
    monthly_net_income: 14000,
    existing_monthly_emis: 2000,
    credit_card_outstanding: 0,
    cibil_score: 670,
    max_dpd_last_12m: 0,
    hard_enquiries_last_30d: 2,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 50000,
    desired_tenure_months: 12
  },
  {
    applicant_id: "PROFILE_08",
    name: "Self-Employed Consultant",
    age: 30,
    city_tier: "Metro",
    employment_type: "Self-Employed",
    employer_category: "CAT_C",
    total_work_exp_months: 60,
    current_job_tenure_months: 36,
    monthly_net_income: 90000,
    existing_monthly_emis: 12000,
    credit_card_outstanding: 0,
    cibil_score: 730,
    max_dpd_last_12m: 0,
    hard_enquiries_last_30d: 2,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 400000,
    desired_tenure_months: 36
  },
  {
    applicant_id: "PROFILE_09",
    name: "Top MNC Corporate Leader",
    age: 32,
    city_tier: "Metro",
    employment_type: "Salaried",
    employer_category: "CAT_A",
    total_work_exp_months: 96,
    current_job_tenure_months: 36,
    monthly_net_income: 200000,
    existing_monthly_emis: 0,
    credit_card_outstanding: 0,
    cibil_score: 820,
    max_dpd_last_12m: 0,
    hard_enquiries_last_30d: 0,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 1500000,
    desired_tenure_months: 48
  },
  {
    applicant_id: "PROFILE_10",
    name: "Exact Policy Boundary Case",
    age: 21,
    city_tier: "Metro",
    employment_type: "Salaried",
    employer_category: "CAT_B",
    total_work_exp_months: 24,
    current_job_tenure_months: 6,
    monthly_net_income: 25000,
    existing_monthly_emis: 3000,
    credit_card_outstanding: 0,
    cibil_score: 700,
    max_dpd_last_12m: 0,
    hard_enquiries_last_30d: 1,
    active_overdue_inr: 0,
    written_off_accounts_count: 0,
    desired_loan_amount: 200000,
    desired_tenure_months: 24
  }
];

let activeProfiles = FALLBACK_PROFILES;

// Currency & Rate Formatters
function formatINR(val) {
  if (val === null || val === undefined || isNaN(val)) return "₹0";
  const num = Math.round(Number(val));
  return "₹" + num.toLocaleString("en-IN");
}

function formatRate(val) {
  if (val === null || val === undefined || isNaN(val)) return "0.00%";
  return Number(val).toFixed(2) + "%";
}

// DOM Elements
const form = document.getElementById("underwriting-form");
const sidebarProfileList = document.getElementById("sidebar-profile-list");
const btnReset = document.getElementById("btn-reset-form");
const statusBanner = document.getElementById("status-banner");

// Summary Card Elements
const elApprovedCount = document.getElementById("val-approved-count");
const elApprovedRate = document.getElementById("val-approved-rate");
const elRejectedCount = document.getElementById("val-rejected-count");
const elBestRate = document.getElementById("val-best-rate");
const elBestLender = document.getElementById("val-best-lender");
const elBestSanction = document.getElementById("val-best-sanction");
const elBestEmi = document.getElementById("val-best-emi");
const elVerdictBadge = document.getElementById("verdict-status-badge");

// Best Offer Card Elements
const elPrimeCard = document.getElementById("prime-offer-card");
const elPrimeInstType = document.getElementById("prime-inst-type");
const elPrimeName = document.getElementById("prime-lender-name");
const elPrimeSub = document.getElementById("prime-lender-sub");
const elPrimeSanction = document.getElementById("prime-sanction");
const elPrimeRate = document.getElementById("prime-rate");
const elPrimeEmi = document.getElementById("prime-emi");
const elPrimeProcFee = document.getElementById("prime-proc-fee");
const elPrimeTenure = document.getElementById("prime-tenure");
const elPrimeTotalCost = document.getElementById("prime-total-cost");
const elPrimeForeclosure = document.getElementById("prime-foreclosure");
const elPrimeLink = document.getElementById("prime-source-link");
const elPrimePolicyText = document.getElementById("prime-policy-text");

// Tips / Prescriptions
const elPrescriptionList = document.getElementById("prescription-list");

// Tab Elements
const countTabEligible = document.getElementById("count-tab-eligible");
const countTabIneligible = document.getElementById("count-tab-ineligible");
const eligibleTbody = document.getElementById("eligible-tbody");
const ineligibleTbody = document.getElementById("ineligible-tbody");

// Initialize on Load
document.addEventListener("DOMContentLoaded", async () => {
  setupTabs();
  setupFormHandlers();
  await initProfiles();
});

// Setup Table Tab Switching
function setupTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      tabBtns.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");
    });
  });
}

// Fetch profiles or bind fallback
async function initProfiles() {
  try {
    const res = await fetch("/api/profiles");
    if (res.ok) {
      const serverProfiles = await res.json();
      if (serverProfiles && serverProfiles.length > 0) {
        activeProfiles = serverProfiles;
      }
    }
  } catch (err) {
    console.log("Using embedded profile scenarios.");
  }
  bindSidebarProfiles();
  // Auto-populate with Profile 1
  if (activeProfiles.length > 0) {
    populateForm(activeProfiles[0]);
    runUnderwriting();
  }
}

// Bind Sidebar Profile Cards
function bindSidebarProfiles() {
  const cards = sidebarProfileList.querySelectorAll(".profile-card");
  cards.forEach(card => {
    card.addEventListener("click", () => {
      cards.forEach(c => c.classList.remove("active"));
      card.classList.add("active");

      const profileId = card.getAttribute("data-id");
      const matched = activeProfiles.find(p => p.applicant_id === profileId);
      if (matched) {
        populateForm(matched);
        runUnderwriting();
      }
    });
  });
}

// Populate Form from Profile
function populateForm(p) {
  document.getElementById("applicant_id").value = p.applicant_id || "CUSTOM_APP";
  document.getElementById("name").value = p.name || "Applicant";
  document.getElementById("age").value = p.age !== undefined ? p.age : 30;
  document.getElementById("city_tier").value = (p.city_tier || "Metro").toLowerCase().includes("non") ? "Non-Metro" : "Metro";
  document.getElementById("employment_type").value = (p.employment_type || "Salaried").toLowerCase().includes("self") ? "Self-Employed" : "Salaried";
  document.getElementById("employer_category").value = p.employer_category || "CAT_B";
  document.getElementById("total_work_exp_months").value = p.total_work_exp_months !== undefined ? p.total_work_exp_months : 24;
  document.getElementById("current_job_tenure_months").value = p.current_job_tenure_months !== undefined ? p.current_job_tenure_months : 12;
  document.getElementById("monthly_net_income").value = p.monthly_net_income || 50000;
  document.getElementById("existing_monthly_emis").value = p.existing_monthly_emis || 0;
  document.getElementById("credit_card_outstanding").value = p.credit_card_outstanding || 0;
  document.getElementById("cibil_score").value = p.cibil_score !== undefined ? p.cibil_score : 750;
  document.getElementById("max_dpd_last_12m").value = p.max_dpd_last_12m || 0;
  document.getElementById("hard_enquiries_last_30d").value = p.hard_enquiries_last_30d || 0;
  document.getElementById("active_overdue_inr").value = p.active_overdue_inr || 0;
  document.getElementById("written_off_accounts_count").value = p.written_off_accounts_count || 0;
  document.getElementById("desired_loan_amount").value = p.desired_loan_amount || 500000;
  document.getElementById("desired_tenure_months").value = p.desired_tenure_months || 36;
}

// Setup Form Submission
function setupFormHandlers() {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    // Clear sidebar selection highlight if user manually submitted custom values
    sidebarProfileList.querySelectorAll(".profile-card").forEach(c => c.classList.remove("active"));
    runUnderwriting();
  });

  btnReset.addEventListener("click", () => {
    form.reset();
    document.getElementById("applicant_id").value = "CUSTOM_APP";
    document.getElementById("cibil_score").value = "750";
    document.getElementById("monthly_net_income").value = "50000";
    document.getElementById("age").value = "28";
    sidebarProfileList.querySelectorAll(".profile-card").forEach(c => c.classList.remove("active"));
  });
}

// Collect form data safely
function getFormData() {
  return {
    applicant_id: document.getElementById("applicant_id").value || "CUSTOM_APP",
    name: document.getElementById("name").value.trim() || "Applicant",
    age: parseInt(document.getElementById("age").value, 10) || 0,
    city_tier: document.getElementById("city_tier").value,
    employment_type: document.getElementById("employment_type").value,
    employer_category: document.getElementById("employer_category").value,
    total_work_exp_months: parseInt(document.getElementById("total_work_exp_months").value, 10) || 0,
    current_job_tenure_months: parseInt(document.getElementById("current_job_tenure_months").value, 10) || 0,
    monthly_net_income: parseFloat(document.getElementById("monthly_net_income").value) || 0,
    existing_monthly_emis: parseFloat(document.getElementById("existing_monthly_emis").value) || 0,
    credit_card_outstanding: parseFloat(document.getElementById("credit_card_outstanding").value) || 0,
    cibil_score: parseInt(document.getElementById("cibil_score").value, 10),
    max_dpd_last_12m: parseInt(document.getElementById("max_dpd_last_12m").value, 10) || 0,
    hard_enquiries_last_30d: parseInt(document.getElementById("hard_enquiries_last_30d").value, 10) || 0,
    active_overdue_inr: parseFloat(document.getElementById("active_overdue_inr").value) || 0,
    written_off_accounts_count: parseInt(document.getElementById("written_off_accounts_count").value, 10) || 0,
    desired_loan_amount: parseFloat(document.getElementById("desired_loan_amount").value) || null,
    desired_tenure_months: parseInt(document.getElementById("desired_tenure_months").value, 10) || null,
  };
}

// Show polite inline status banner
function showStatusBanner(msg, isError = false) {
  if (!statusBanner) return;
  statusBanner.textContent = msg;
  statusBanner.style.display = "flex";
  if (isError) {
    statusBanner.style.background = "rgba(248, 113, 113, 0.15)";
    statusBanner.style.borderColor = "var(--block)";
    statusBanner.style.color = "var(--block)";
  } else {
    statusBanner.style.background = "rgba(16, 185, 129, 0.15)";
    statusBanner.style.borderColor = "var(--pass)";
    statusBanner.style.color = "var(--pass)";
  }
}

function hideStatusBanner() {
  if (statusBanner) statusBanner.style.display = "none";
}

// Execute Underwriting API
async function runUnderwriting() {
  hideStatusBanner();
  const applicantPayload = getFormData();
  const submitBtn = document.getElementById("btn-submit");
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span>Checking 20 Banks...</span>`;

  try {
    const response = await fetch("/api/underwrite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(applicantPayload)
    });

    if (!response.ok) {
      throw new Error(`Server returned status ${response.status}`);
    }

    const data = await response.json();
    if (data && data.status === "success") {
      renderResults(data);
    } else {
      showStatusBanner("Unable to calculate eligibility: " + (data.message || "Invalid input parameters"), true);
    }
  } catch (err) {
    console.warn("API request issue:", err);
    showStatusBanner("Notice: PLE-Birbal server is running locally on port 5050. Check terminal to ensure 'python server.py' is active.", true);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span>Check Loan Offers Now</span> <span class="btn-arrow" aria-hidden="true">→</span>`;
  }
}

// Render Results
function renderResults(data) {
  const { decision, prescriptions } = data;
  const summary = decision.summary;
  const best = decision.best_option;

  // 1. Summary Metrics
  elApprovedCount.textContent = `${summary.approved_count} / ${summary.total_lenders_evaluated}`;
  elApprovedRate.textContent = `${summary.approval_rate_percent}% Approval Rate`;
  elRejectedCount.textContent = `${summary.rejected_count} Banks`;

  if (best) {
    elVerdictBadge.textContent = "LOAN APPROVED // OFFERS READY";
    elVerdictBadge.className = "verdict-badge";
    elBestRate.textContent = formatRate(best.financials.interest_rate_pct);
    elBestLender.textContent = best.lender_name;
    elBestSanction.textContent = formatINR(best.financials.sanction_amount);
    elBestEmi.textContent = `${formatINR(best.financials.monthly_emi)} / Month EMI`;

    // 2. Best Offer Spotlight
    elPrimeCard.style.display = "block";
    elPrimeInstType.textContent = (best.institution_type || "BANK").toUpperCase();
    elPrimeName.textContent = best.lender_name;
    elPrimeSub.textContent = `Lowest interest rate of ${formatRate(best.financials.interest_rate_pct)} p.a. with minimal EMI and lowest total cost of borrowing.`;
    elPrimeSanction.textContent = formatINR(best.financials.sanction_amount);
    elPrimeRate.textContent = formatRate(best.financials.interest_rate_pct);
    elPrimeEmi.textContent = formatINR(best.financials.monthly_emi);
    elPrimeProcFee.textContent = formatINR(best.financials.processing_fee_inr);
    elPrimeTenure.textContent = `${best.financials.tenure_months} Months`;
    elPrimeTotalCost.textContent = formatINR(best.financials.total_cost_of_credit);
    elPrimeForeclosure.textContent = best.financials.foreclosure_penalty || "Standard RBI Prepayment Guidelines";
    elPrimePolicyText.textContent = best.financials.unlisted_rules_method_summary || "Matched your salary, corporate tier, and CIBIL score.";

    if (best.financials.source) {
      elPrimeLink.href = best.financials.source;
      elPrimeLink.style.display = "inline-flex";
    } else {
      elPrimeLink.style.display = "none";
    }
  } else {
    // Zero Approval Case
    elVerdictBadge.textContent = "NOT ELIGIBLE // CRITERIA NOT MET";
    elVerdictBadge.className = "verdict-badge knockout";
    elBestRate.textContent = "N/A";
    elBestLender.textContent = "No Banks Approved";
    elBestSanction.textContent = "₹0";
    elBestEmi.textContent = "₹0 / Month EMI";

    elPrimeCard.style.display = "block";
    elPrimeInstType.textContent = "NOTICE";
    elPrimeName.textContent = "Not Eligible at Current Banks";
    elPrimeSub.textContent = "Applicant did not meet the mandatory criteria across the 20 banks.";
    elPrimeSanction.textContent = "₹0";
    elPrimeRate.textContent = "—";
    elPrimeEmi.textContent = "₹0";
    elPrimeProcFee.textContent = "₹0";
    elPrimeTenure.textContent = "0 Months";
    elPrimeTotalCost.textContent = "₹0";
    elPrimeForeclosure.textContent = "N/A";
    elPrimeLink.style.display = "none";
    elPrimePolicyText.textContent = "See the 'Not Eligible' tab below for the exact reasons.";
  }

  // 3. What-If Advice Cards
  renderTips(prescriptions);

  // 4. Tab Counters & Tables
  const eligibleOffers = decision.eligible_offers || decision.ranked_eligible_offers || [];
  const ineligibleLenders = decision.ineligible_lenders || [];

  countTabEligible.textContent = eligibleOffers.length;
  countTabIneligible.textContent = ineligibleLenders.length;

  renderEligibleTable(eligibleOffers);
  renderIneligibleTable(ineligibleLenders);
}

// Render Improvement Tips
function renderTips(prescriptions) {
  elPrescriptionList.innerHTML = "";

  if (!prescriptions || prescriptions.length === 0) {
    elPrescriptionList.innerHTML = `
      <div class="tip-card" style="border-left-color: var(--edge);">
        <div class="tip-title">GREAT PROFILE</div>
        <div class="tip-impact text-muted">You are already qualifying for the top lenders at competitive rates. No urgent actions needed.</div>
      </div>
    `;
    return;
  }

  prescriptions.forEach((p, idx) => {
    const card = document.createElement("div");
    card.className = "tip-card";

    const title = p.title || p.action || `Tip ${idx + 1}`;
    const impactBadge = p.impact || "Action Available";
    const actionText = p.action || "";
    const explanationText = p.explanation || "";
    const bestLender = p.new_best_lender || "";
    const newRate = p.new_rate ? formatRate(p.new_rate) : "";

    card.innerHTML = `
      <div class="tip-head">
        <span class="tip-title">[TIP ${idx + 1}] ${escapeHtml(title)}</span>
        <span class="tip-badge font-mono">${escapeHtml(impactBadge)}</span>
      </div>
      ${actionText ? `
      <div class="tip-action">
        <strong>ACTION:</strong> ${escapeHtml(actionText)}
      </div>` : ''}
      ${explanationText ? `
      <div class="tip-impact">
        ${escapeHtml(explanationText)}
      </div>` : ''}
      ${bestLender ? `
      <div class="tip-partner">
        <span>Target Bank: ${escapeHtml(bestLender)}</span>
        ${newRate ? `<span>Expected Rate: ${newRate}</span>` : ''}
      </div>` : ''}
    `;

    elPrescriptionList.appendChild(card);
  });
}

// Render Eligible Banks Table
function renderEligibleTable(offers) {
  eligibleTbody.innerHTML = "";

  if (!offers || offers.length === 0) {
    eligibleTbody.innerHTML = `
      <tr>
        <td colspan="9" style="text-align: center; color: var(--ink-secondary); padding: 28px;">
          No banks currently eligible. Switch to "Not Eligible" tab to view why each bank rejected your profile.
        </td>
      </tr>
    `;
    return;
  }

  offers.forEach((item, index) => {
    const rank = index + 1;
    const fin = item.financials;
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>
        <span class="rank-badge ${rank === 1 ? 'top-pick' : ''}">#${rank}</span>
      </td>
      <td>
        <div class="b-name">${escapeHtml(item.lender_name)}</div>
        <div class="b-product font-mono">${escapeHtml(item.product_name || "Personal Loan")}</div>
      </td>
      <td class="font-mono text-muted" style="font-size: 11px;">${escapeHtml(item.institution_type || "Bank")}</td>
      <td class="font-mono text-pass font-bold">${formatRate(fin.interest_rate_pct)}</td>
      <td class="font-mono font-bold">${formatINR(fin.sanction_amount)}</td>
      <td class="font-mono">${fin.tenure_months}m</td>
      <td class="font-mono">${formatINR(fin.monthly_emi)}</td>
      <td class="font-mono text-muted">${formatINR(fin.total_cost_of_credit)}</td>
      <td>
        ${fin.source ? `<a href="${escapeHtml(fin.source)}" target="_blank" rel="noopener noreferrer" class="bank-link">Apply ↗</a>` : '—'}
      </td>
    `;

    eligibleTbody.appendChild(tr);
  });
}

// Render Ineligible Banks Table
function renderIneligibleTable(ineligible) {
  ineligibleTbody.innerHTML = "";

  if (!ineligible || ineligible.length === 0) {
    ineligibleTbody.innerHTML = `
      <tr>
        <td colspan="3" style="text-align: center; color: var(--pass); padding: 28px;">
          All 20 banks evaluated and approved your profile!
        </td>
      </tr>
    `;
    return;
  }

  ineligible.forEach(item => {
    const tr = document.createElement("tr");

    const reasonsHtml = item.rejection_reasons.map(r => {
      const match = r.match(/^\[(.*?)\]\s*\[(.*?)\]\s*(.*)$/);
      if (match) {
        return `
          <div class="reason-item">
            <span class="reason-tag">${escapeHtml(match[1])}</span>
            <span>${escapeHtml(match[3])}</span>
          </div>
        `;
      }
      return `<div class="reason-item">• ${escapeHtml(r)}</div>`;
    }).join("");

    tr.innerHTML = `
      <td>
        <div class="b-name">${escapeHtml(item.lender_name)}</div>
      </td>
      <td class="font-mono text-muted" style="font-size: 11px;">${escapeHtml(item.institution_type || "Bank")}</td>
      <td>
        ${reasonsHtml}
      </td>
    `;

    ineligibleTbody.appendChild(tr);
  });
}

// HTML escape helper
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
