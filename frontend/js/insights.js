// =========================================================
// ApexPay - js/insights.js
// =========================================================

document.addEventListener("DOMContentLoaded", async () => {
  const aiBody = document.getElementById("aiBody");
  const reviewDiningBtn = document.getElementById("reviewDiningBtn");
  const regenerateBtn = document.getElementById("regenerateBtn");
  const viewAllBtn = document.getElementById("viewAllBtn");
  const donutChart = document.getElementById("donutChart");
  const progressFill = document.getElementById("progressFill");
  const addToGoalBtn = document.getElementById("addToGoalBtn");

  if (viewAllBtn) viewAllBtn.addEventListener("click", () => (window.location.href = "transactions.html"));
  if (addToGoalBtn) addToGoalBtn.addEventListener("click", () => showToast("Add to Goal is coming soon."));

  let currentInsight = null;

  await loadInsights();

  if (reviewDiningBtn) {
    reviewDiningBtn.addEventListener("click", () => (window.location.href = "transactions.html"));
  }

  if (regenerateBtn) {
    regenerateBtn.addEventListener("click", handleRegenerate);
  }

  // ---------------------------------------------------
  async function loadInsights() {
    try {
      const data = await Api.get("/insights");
      populateMonthlyAnalysis(data.monthlyAnalysis);
      populateGoal(data.activeGoal);
      populateCategoryBreakdown(data.categoryBreakdown);
      populateSmartTips(data.smartTips || []);
    } catch (err) {
      showToast(err.message || "Couldn't load insights.", "error");
    }
  }

  function populateMonthlyAnalysis(insight) {
    currentInsight = insight;
    if (!aiBody) return;

    if (!insight) {
      aiBody.textContent = "We're still gathering data about your spending. Check back soon for a personalized analysis.";
      return;
    }

    aiBody.textContent = insight.body;
  }

  function populateGoal(goal) {
    if (!goal) return;

    const nameEl = document.querySelector(".goal-name");
    const targetTxtEl = document.querySelector(".goal-target-txt");
    const amountEl = document.querySelector(".goal-amount");
    const ofTxtEl = document.querySelector(".goal-of-txt");
    const statusEl = document.querySelector(".goal-status");

    if (nameEl) nameEl.textContent = goal.name;
    if (amountEl) amountEl.textContent = `$${Math.round(goal.current).toLocaleString("en-US")}`;
    if (ofTxtEl) ofTxtEl.textContent = `of $${Math.round(goal.target).toLocaleString("en-US")}`;

    if (targetTxtEl && goal.targetDate) {
      const d = new Date(goal.targetDate);
      const label = d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
      targetTxtEl.textContent = `Target: ${label}`;
    }

    if (progressFill) {
      requestAnimationFrame(() => {
        progressFill.style.width = `${Math.min(goal.progressPct, 100)}%`;
      });
    }

    if (statusEl) {
      statusEl.textContent = goal.onTrack
        ? "↗ On track to meet your goal!"
        : "⚠ Behind schedule — consider increasing contributions.";
      statusEl.style.color = goal.onTrack ? "var(--success)" : "var(--warning)";
    }
  }

  function populateCategoryBreakdown(breakdown) {
    if (!breakdown) return;

    const valEl = document.querySelector(".donut-val");
    if (valEl) {
      valEl.textContent = `$${Math.round(breakdown.totalSpend).toLocaleString("en-US")}`;
    }

    const categories = breakdown.categories || [];
    if (!categories.length) return;

    // Build conic-gradient for the donut
    let cumulative = 0;
    const stops = categories
      .map((c) => {
        const start = cumulative;
        cumulative += c.pct;
        return `${c.color} ${start}% ${cumulative}%`;
      })
      .join(", ");

    if (donutChart) {
      donutChart.style.background = `conic-gradient(${stops})`;
    }

    // Update legend rows
    const legend = document.querySelector(".legend");
    if (legend) {
      legend.innerHTML = categories
        .map(
          (c) => `
            <div class="legend-row">
              <div class="legend-left">
                <div class="legend-dot" style="background:${c.color}"></div>
                <span class="legend-name">${escapeHtml(c.category)}</span>
              </div>
              <span class="legend-pct">${c.pct}%</span>
            </div>
          `
        )
        .join("");
    }
  }

  function populateSmartTips(tips) {
    if (!tips.length) return;

    const tipItems = document.querySelectorAll(".tip-item");
    const colorMap = { "#F59E0B": "yellow", "#0058be": "blue", "#10B981": "green" };
    const emojiMap = {
      subscriptions: "⚡",
      shopping_basket: "🛒",
      account_balance: "🏦",
      lightbulb: "💡",
      savings: "🐖",
    };

    // If there are more tips than rendered <div class="tip-item">, build fresh markup
    const container = tipItems.length ? tipItems[0].parentElement : null;
    if (!container) return;

    container.innerHTML = tips
      .map((tip) => {
        const colorClass = colorMap[tip.iconColor] || "blue";
        const emoji = emojiMap[tip.icon] || "💡";
        return `
          <div class="tip-item">
            <div class="tip-bullet ${colorClass}">${emoji}</div>
            <div>
              <div class="tip-content-title">${escapeHtml(tip.title)}</div>
              <div class="tip-content-text">${escapeHtml(tip.description)}</div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  // ---------------------------------------------------
  async function handleRegenerate() {
    const original = regenerateBtn.textContent;
    regenerateBtn.disabled = true;
    regenerateBtn.textContent = "🔄 Refreshing...";

    aiBody.style.opacity = "0.5";

    try {
      const data = await Api.post("/insights/generate", {});

      if (!data.generated) {
        showToast(data.reason || "Couldn't generate a new insight right now.", "error");
        if (data.insight) populateMonthlyAnalysis(data.insight);
        return;
      }

      populateMonthlyAnalysis(data.insight);
      showToast("Insight refreshed with the latest AI analysis.", "success");
    } catch (err) {
      showToast(err.message || "Couldn't refresh insight.", "error");
    } finally {
      regenerateBtn.disabled = false;
      regenerateBtn.textContent = original;
      aiBody.style.opacity = "1";
    }
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
});
