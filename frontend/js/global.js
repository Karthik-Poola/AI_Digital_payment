// =========================================================
// ApexPay - js/global.js
// API client + auth helpers + shared UI behaviors
// Loaded on every page before the page-specific script.
// =========================================================

// If served by the Flask backend directly (same origin), use a
// relative /api path. Otherwise (e.g. opening the HTML files
// directly via file:// or a separate dev server), fall back to
// localhost:5000. Override anytime by setting
// window.APEXPAY_API_BASE before this script loads.
const API_BASE =
  window.APEXPAY_API_BASE ||
  (window.location.protocol.startsWith("http") ? `${window.location.origin}/api` : "http://localhost:5000/api");

const AUTH_PAGES = ["login.html", "register.html", "index.html", ""];

const Auth = {
  getAccessToken() {
    return localStorage.getItem("apexpay_access_token");
  },
  getRefreshToken() {
    return localStorage.getItem("apexpay_refresh_token");
  },
  getUser() {
    const raw = localStorage.getItem("apexpay_user");
    return raw ? JSON.parse(raw) : null;
  },
  setSession({ accessToken, refreshToken, user }) {
    if (accessToken) localStorage.setItem("apexpay_access_token", accessToken);
    if (refreshToken) localStorage.setItem("apexpay_refresh_token", refreshToken);
    if (user) localStorage.setItem("apexpay_user", JSON.stringify(user));
  },
  updateUser(user) {
    localStorage.setItem("apexpay_user", JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem("apexpay_access_token");
    localStorage.removeItem("apexpay_refresh_token");
    localStorage.removeItem("apexpay_user");
  },
  isLoggedIn() {
    return !!this.getAccessToken();
  },
  logout() {
    this.clear();
    window.location.href = "login.html";
  },
};

/**
 * Core fetch wrapper.
 * - Attaches JWT Authorization header
 * - Auto-retries once with a refreshed access token on 401
 * - Throws ApiError with .status and .data on failure
 */
class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function apiFetch(path, options = {}) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

  const doFetch = async () => {
    const headers = Object.assign({}, options.headers || {});
    const token = Auth.getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    return fetch(url, { ...options, headers });
  };

  let res = await doFetch();

  // Try to refresh the access token once on 401
  if (res.status === 401 && Auth.getRefreshToken() && !options._retried) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      res = await doFetch();
    }
  }

  const contentType = res.headers.get("content-type") || "";
  let data = null;
  if (contentType.includes("application/json")) {
    data = await res.json().catch(() => null);
  }

  if (!res.ok) {
    const message = (data && (data.error || data.message)) || `Request failed (${res.status})`;
    throw new ApiError(message, res.status, data);
  }

  return data !== null ? data : res;
}

async function tryRefreshToken() {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { Authorization: `Bearer ${Auth.getRefreshToken()}` },
    });
    if (!res.ok) {
      Auth.clear();
      return false;
    }
    const data = await res.json();
    Auth.setSession({ accessToken: data.accessToken });
    return true;
  } catch {
    Auth.clear();
    return false;
  }
}

// Convenience helpers
const Api = {
  get: (path) => apiFetch(path, { method: "GET" }),
  post: (path, body) => apiFetch(path, { method: "POST", body: JSON.stringify(body || {}) }),
  put: (path, body) => apiFetch(path, { method: "PUT", body: JSON.stringify(body || {}) }),
  patch: (path, body) => apiFetch(path, { method: "PATCH", body: JSON.stringify(body || {}) }),
  delete: (path) => apiFetch(path, { method: "DELETE" }),
};

// =========================================================
// Page guard: redirect unauthenticated users away from the
// app pages, and logged-in users away from auth pages.
// =========================================================
(function pageGuard() {
  const page = window.location.pathname.split("/").pop();
  const isAuthPage = AUTH_PAGES.includes(page);

  if (!isAuthPage && !Auth.isLoggedIn()) {
    window.location.href = "login.html";
  }
})();

// =========================================================
// Shared UI: toast notifications
// =========================================================
function showToast(message, type = "default", duration = 3000) {
  let toast = document.getElementById("globalToast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "globalToast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = "";
  if (type === "error") toast.classList.add("error");
  if (type === "success") toast.classList.add("success");

  requestAnimationFrame(() => toast.classList.add("show"));
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove("show"), duration);
}

// =========================================================
// Shared UI: avatar + dropdown menu, populated with user info
// =========================================================
function initAvatarMenu() {
  const avatarEls = document.querySelectorAll(".avatar");
  const user = Auth.getUser();

  avatarEls.forEach((avatar) => {
    if (user && user.avatarInitials) {
      avatar.textContent = user.avatarInitials;
    }

    // Build dropdown if not present
    let menu = avatar.parentElement.querySelector(".avatar-menu");
    if (!menu) {
      menu = document.createElement("div");
      menu.className = "avatar-menu";
      menu.innerHTML = `
        <a href="profile.html">👤 My Profile</a>
        <a href="profile.html">⚙️ Account Settings</a>
        <hr/>
        <button class="danger" id="logoutBtn">🚪 Log Out</button>
      `;
      avatar.parentElement.style.position = "relative";
      avatar.parentElement.appendChild(menu);

      menu.querySelector("#logoutBtn").addEventListener("click", () => Auth.logout());
    }

    avatar.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.toggle("open");
    });
  });

  document.addEventListener("click", () => {
    document.querySelectorAll(".avatar-menu.open").forEach((m) => m.classList.remove("open"));
  });
}

// =========================================================
// Shared UI: notification bell -> simple toast for now
// =========================================================
function initNotificationBell() {
  document.querySelectorAll("#bellBtn").forEach((btn) => {
    btn.addEventListener("click", () => {
      showToast("You're all caught up — no new notifications.");
    });
  });
}

// =========================================================
// Format helpers
// =========================================================
function formatCurrency(amount, currency = "USD") {
  const n = Number(amount || 0);
  return n.toLocaleString("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  });
}

function formatRelativeDate(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  const time = date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });

  if (diffDays === 0) return `Today, ${time}`;
  if (diffDays === 1) return `Yesterday, ${time}`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

// =========================================================
// Init shared UI on DOM ready
// =========================================================
document.addEventListener("DOMContentLoaded", () => {
  initAvatarMenu();
  initNotificationBell();
});
