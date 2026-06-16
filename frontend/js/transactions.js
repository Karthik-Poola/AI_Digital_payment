// =========================================================
// ApexPay - js/transactions.js
// =========================================================

const FRAUD_BADGE_CLASS = {
  success: "fraud-success",
  info: "fraud-info",
  warning: "fraud-warning",
  danger: "fraud-danger",
};

const FRAUD_BADGE_ICON = {
  check_circle: "✅",
  shield: "🛡️",
  warning: "⚠️",
  gpp_bad: "⛔",
};

const CATEGORY_ICON_MAP = {
  "Software Subscriptions": "💼",
  "Uncategorized": "🌐",
  "Internal Transfer": "🏦",
  "Digital Assets": "⚠️",
  "Travel & Transit": "✈️",
  "Groceries": "🛒",
  "Income": "⬇️",
  "Entertainment": "📺",
  "Transfer": "↗️",
  "Transfer Received": "⬇️",
};

document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("txnSearch");
  const dateFilter = document.getElementById("dateFilter");
  const categoryFilter = document.getElementById("categoryFilter");
  const exportBtn = document.getElementById("exportBtn");
  const tableBody = document.getElementById("tableBody");
  const tableInfo = document.getElementById("tableInfo");
  const pager = document.getElementById("pager");

  const PAGE_SIZE = 5;
  let currentPage = 1;
  let debounceTimer = null;

  // Map <select id="dateFilter"> values (days) to API range codes
  const RANGE_MAP = { "7": "7d", "30": "30d", "90": "90d", "365": "all" };

  loadTransactions();

  searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      loadTransactions();
    }, 350);
  });

  dateFilter.addEventListener("change", () => {
    currentPage = 1;
    loadTransactions();
  });

  categoryFilter.addEventListener("change", () => {
    currentPage = 1;
    loadTransactions();
  });

  exportBtn.addEventListener("click", handleExport);

  async function loadTransactions() {
    tableBody.innerHTML = `<div class="loading-row"><div class="spinner"></div> Loading transactions...</div>`;
    tableInfo.textContent = "Loading...";
    pager.innerHTML = "";

    const params = buildParams();

    try {
      const data = await Api.get(`/transactions?${params.toString()}`);
      renderTable(data.items || []);
      renderTableInfo(data);
      renderPager(data);
    } catch (err) {
      tableBody.innerHTML = `<div class="loading-row">Couldn't load transactions.</div>`;
      tableInfo.textContent = "";
      showToast(err.message || "Couldn't load transactions.", "error");
    }
  }

  function buildParams() {
    const params = new URLSearchParams();
    params.set("page", currentPage);
    params.set("pageSize", PAGE_SIZE);

    const search = searchInput.value.trim();
    if (search) params.set("search", search);

    const range = RANGE_MAP[dateFilter.value] || "30d";
    params.set("range", range);

    const category = categoryFilter.value;
    if (category && category !== "all") {
      params.set("category", categorySlugToName(category));
    }

    return params;
  }

  function renderTable(items) {
    if (!items.length) {
      tableBody.innerHTML = `<div class="loading-row">No transactions found.</div>`;
      return;
    }

    tableBody.innerHTML = items.map(renderRow).join("");
  }

  function renderRow(tx) {
    const isCredit = tx.direction === "credit";
    const amountClass = isCredit ? "pos" : "neg";
    const sign = isCredit ? "+" : "-";
    const struck = tx.status === "blocked" ? "strike" : "";
    const amountColor = tx.status === "blocked" ? "muted" : "";

    const fraud = tx.fraudCheck || {};
    const badgeClass = FRAUD_BADGE_CLASS[fraud.type] || "fraud-info";
    const badgeIcon = FRAUD_BADGE_ICON[fraud.icon] || "ℹ️";

    const icon = CATEGORY_ICON_MAP[tx.category] || "🧾";

    const dateLabel = formatTxDate(tx.occurredAt);
    const dateExtra = tx.status === "action_required" ? `<span class="date-flag">Action Required •</span> ` : "";

    return `
      <div class="t-row">
        <div class="t-cell recip">
          <div class="recip-icon">${icon}</div>
          <div>
            <div class="recip-name">${escapeHtml(tx.recipientName)}</div>
            <div class="recip-date">${dateExtra}${dateLabel}</div>
          </div>
        </div>
        <div class="t-cell">
          <span class="cat-pill">${escapeHtml(tx.category)}</span>
        </div>
        <div class="t-cell">
          <span class="fraud-badge ${badgeClass}">${badgeIcon} ${escapeHtml(fraud.label || "")}</span>
        </div>
        <div class="t-cell right amount ${amountClass} ${struck} ${amountColor}">
          ${sign}$${tx.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
        </div>
      </div>
    `;
  }

  function renderTableInfo(data) {
    const start = (data.page - 1) * data.pageSize + 1;
    const end = Math.min(data.page * data.pageSize, data.total);
    if (data.total === 0) {
      tableInfo.textContent = "No transactions found";
    } else {
      tableInfo.textContent = `Showing ${start} to ${end} of ${data.total} transactions`;
    }
  }

  function renderPager(data) {
    const totalPages = data.totalPages || 1;
    if (totalPages <= 1) {
      pager.innerHTML = "";
      return;
    }

    let html = `<button class="pager-btn" data-page="${currentPage - 1}" ${currentPage === 1 ? "disabled" : ""}>‹</button>`;

    for (let p = 1; p <= totalPages; p++) {
      html += `<button class="pager-btn ${p === currentPage ? "active" : ""}" data-page="${p}">${p}</button>`;
    }

    html += `<button class="pager-btn" data-page="${currentPage + 1}" ${currentPage === totalPages ? "disabled" : ""}>›</button>`;

    pager.innerHTML = html;

    pager.querySelectorAll(".pager-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const page = parseInt(btn.dataset.page, 10);
        if (page < 1 || page > totalPages || page === currentPage) return;
        currentPage = page;
        loadTransactions();
      });
    });
  }

  async function handleExport() {
    const params = buildParams();
    params.delete("page");
    params.delete("pageSize");

    const originalText = exportBtn.textContent;
    exportBtn.disabled = true;
    exportBtn.textContent = "Exporting...";

    try {
      const token = Auth.getAccessToken();
      const res = await fetch(`${API_BASE}/transactions/export?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Export failed");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "transactions.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      showToast("Transactions exported.", "success");
    } catch (err) {
      showToast(err.message || "Export failed.", "error");
    } finally {
      exportBtn.disabled = false;
      exportBtn.textContent = originalText;
    }
  }

  // ---- Helpers ----
  function categorySlugToName(slug) {
    const map = {
      software: "Software Subscriptions",
      travel: "Travel & Transit",
      groceries: "Groceries",
      entertainment: "Entertainment",
      income: "Income",
      digital: "Digital Assets",
    };
    return map[slug] || slug;
  }

  function formatTxDate(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    const dateStr = date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    const timeStr = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
    return `${dateStr} • ${timeStr}`;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
});
