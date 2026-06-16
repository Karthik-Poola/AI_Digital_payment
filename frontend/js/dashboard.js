// =========================================================
// ApexPay - js/dashboard.js
// =========================================================

document.addEventListener("DOMContentLoaded", async () => {
  const balanceNumEl = document.getElementById("balanceNum");
  const chartBarsEl = document.getElementById("chartBars");
  const chartDaysEl = document.getElementById("chartDays");
  const aiLinkEl = document.getElementById("aiLink");
  const pageTitleEl = document.querySelector(".page-title");

  const addMoneyBtn = document.getElementById("addMoneyBtn");
  const sendBtn = document.getElementById("sendBtn");
  const requestBtn = document.getElementById("requestBtn");

  // ---- Wire up static buttons ----
  if (sendBtn) sendBtn.addEventListener("click", () => (window.location.href = "transfer.html"));
  if (requestBtn) requestBtn.addEventListener("click", () => showToast("Request Money is coming soon."));
  if (addMoneyBtn) addMoneyBtn.addEventListener("click", () => showToast("Add Money is coming soon."));

  // "New" tile always jumps to transfer with no prefill
  const newTile = document.querySelector(".contact-item .c-add");
  if (newTile) {
    newTile.closest(".contact-item").addEventListener("click", () => (window.location.href = "transfer.html"));
  }

  renderLoadingState();

  try {
    const data = await Api.get("/dashboard/summary");
    populateGreeting(data);
    populateBalance(data);
    populateCashFlow(data.cashFlow || []);
    populateAiSnippet(data.aiHealthSnippet);
    populateRecentActivity(data.recentActivity || []);
    populateQuickTransfer(data.quickTransferContacts || []);
  } catch (err) {
    showToast(err.message || "Couldn't load dashboard data.", "error");
    renderErrorState();
  }

  // ---------------------------------------------------
  function renderLoadingState() {
    if (chartBarsEl) {
      chartBarsEl.innerHTML = `<div class="loading-row"><div class="spinner"></div> Loading chart...</div>`;
    }
  }

  function renderErrorState() {
    if (chartBarsEl) {
      chartBarsEl.innerHTML = `<div class="loading-row">Couldn't load cash flow data.</div>`;
    }
  }

  function populateGreeting(data) {
    const name = (data.user && data.user.fullName) || Auth.getUser()?.fullName || "there";
    const firstName = name.split(" ")[0];
    if (pageTitleEl) pageTitleEl.textContent = `Good morning, ${firstName}.`;
  }

  function populateBalance(data) {
    if (!balanceNumEl) return;
    const balance = Number(data.balance || 0);
    const whole = Math.floor(balance).toLocaleString("en-US");
    balanceNumEl.textContent = whole;

    // Update +X.X% badge if present
    const badge = document.querySelector(".badge-up");
    if (badge && typeof data.balanceChangePct === "number") {
      const pct = data.balanceChangePct;
      const sign = pct >= 0 ? "+" : "";
      badge.textContent = `${sign}${pct}%`;
      badge.style.background = pct >= 0 ? "var(--success-bg)" : "var(--danger-bg)";
      badge.style.color = pct >= 0 ? "#065f46" : "#991b1b";
    }
  }

  function populateCashFlow(cashFlow) {
    if (!chartBarsEl || !chartDaysEl) return;

    if (!cashFlow.length) {
      chartBarsEl.innerHTML = `<div class="loading-row">No cash flow data yet.</div>`;
      chartDaysEl.innerHTML = "";
      return;
    }

    // Determine max total (inflow+outflow) for scaling bars to 100%
    const maxTotal = Math.max(
      ...cashFlow.map((d) => (d.inflow || 0) + (d.outflow || 0)),
      1
    );

    chartBarsEl.innerHTML = cashFlow
      .map((d) => {
        const total = (d.inflow || 0) + (d.outflow || 0);
        const totalPct = Math.max((total / maxTotal) * 100, 2);
        const outflowPct = total ? ((d.outflow || 0) / total) * 100 : 0;
        const inflowPct = total ? ((d.inflow || 0) / total) * 100 : 0;

        return `
          <div class="chart-bar-col" title="In: $${(d.inflow || 0).toFixed(2)} / Out: $${(d.outflow || 0).toFixed(2)}">
            <div class="chart-bar" style="height:${totalPct}%;">
              <div class="chart-bar-segment light" style="height:${inflowPct}%;"></div>
              <div class="chart-bar-segment dark" style="height:${outflowPct}%;"></div>
            </div>
          </div>
        `;
      })
      .join("");

    chartDaysEl.innerHTML = cashFlow
      .map((d) => `<div class="chart-day">${d.day}</div>`)
      .join("");
  }

  function populateAiSnippet(snippet) {
    const aiTextEl = document.querySelector(".ai-text");
    if (!aiTextEl) return;

    if (!snippet) {
      aiTextEl.textContent = "We're still gathering data about your spending. Check back soon for personalized insights.";
      return;
    }

    // snippet.body is plain text from the backend; render it directly.
    aiTextEl.textContent = snippet.body;

    if (aiLinkEl && snippet.cta) {
      aiLinkEl.textContent = `${snippet.cta.label} →`;
      aiLinkEl.href = snippet.cta.link && snippet.cta.link.includes("insight")
        ? "insights.html"
        : "transactions.html";
    }
  }

  function populateRecentActivity(activity) {
    const container = document.querySelector(".card.mt-20");
    if (!container) return;

    const list = container.querySelector("div:not(.activity-head)");
    // Find the wrapper div that holds .txn-row elements (last direct div child)
    const wrapper = [...container.children].find(
      (el) => el.tagName === "DIV" && !el.classList.contains("activity-head")
    );
    if (!wrapper) return;

    if (!activity.length) {
      wrapper.innerHTML = `<div class="loading-row">No recent activity yet.</div>`;
      return;
    }

    const iconBgMap = {
      storefront: "#f0fdf4",
      flight: "#eff6ff",
      south: "#f0fdf4",
      smart_display: "#fef2f2",
      business_center: "#eff6ff",
      receipt_long: "#f3f4f6",
    };
    const iconEmojiMap = {
      storefront: "🛒",
      flight: "✈️",
      south: "⬇️",
      smart_display: "📺",
      business_center: "💼",
      receipt_long: "🧾",
      send: "↗️",
      error: "⚠️",
      account_balance: "🏦",
      public: "🌐",
    };

    wrapper.innerHTML = activity
      .map((tx) => {
        const bg = iconBgMap[tx.icon] || "#f3f4f6";
        const emoji = iconEmojiMap[tx.icon] || "🧾";
        const amountClass = tx.isCredit ? "pos" : "neg";
        return `
          <div class="txn-row">
            <div class="txn-icon" style="background:${bg}">${emoji}</div>
            <div class="txn-info">
              <div class="txn-name">${escapeHtml(tx.name)}</div>
              <div class="txn-meta">${formatRelativeDate(tx.occurredAt)} · ${escapeHtml(tx.category)}</div>
            </div>
            <div class="txn-amount ${amountClass}">${tx.amount}</div>
          </div>
        `;
      })
      .join("");
  }

  function populateQuickTransfer(contacts) {
    const row = document.querySelector(".contact-row");
    if (!row) return;

    // Keep the "New" tile, replace the rest with live contacts
    const newTile = row.querySelector(".contact-item");
    const newTileHtml = newTile ? newTile.outerHTML : "";

    if (!contacts.length) return; // keep static fallback chips

    const palette = ["#8b5cf6", "#0891b2", "#059669", "#374151", "#d97706", "#2563eb"];

    const chipsHtml = contacts
      .map((c, i) => {
        const bg = c.bg && c.bg.startsWith("#") && c.bg !== "#1f2937" ? c.bg : palette[i % palette.length];
        const label = c.icon ? "🏢" : c.initials;
        return `
          <div class="contact-item" data-identifier="${escapeAttr(c.identifier)}" data-name="${escapeAttr(c.name)}">
            <div class="c-avatar" style="background:${bg}">${label}</div>
            <div class="c-name">${escapeHtml(firstWord(c.name))}</div>
          </div>
        `;
      })
      .join("");

    row.innerHTML = newTileHtml + chipsHtml;

    // Re-bind "New" tile
    const reNewTile = row.querySelector(".c-add");
    if (reNewTile) {
      reNewTile.closest(".contact-item").addEventListener("click", () => (window.location.href = "transfer.html"));
    }

    // Bind contact chips -> prefill transfer recipient by identifier (email)
    row.querySelectorAll(".contact-item[data-identifier]").forEach((item) => {
      item.style.cursor = "pointer";
      item.addEventListener("click", () => {
        sessionStorage.setItem("apexpay_prefill_recipient", item.dataset.identifier);
        window.location.href = "transfer.html";
      });
    });
  }

  function firstWord(name) {
    return String(name || "").split(" ")[0];
  }

  function escapeAttr(str) {
    return escapeHtml(str).replace(/"/g, "&quot;");
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
});
