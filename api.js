/* ═══════════════════════════════════════════════════════════════════════
   BilimChallenge — umumiy API mijoz va autentifikatsiya yordamchisi
   Barcha sahifalar shu faylni ulaydi (config.js dan keyin).
   ═══════════════════════════════════════════════════════════════════════ */

const BC = (function () {
  const TOKEN_KEY = "bc_session_token";
  const USER_KEY = "bc_user_cache";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }
  function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  }
  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
  function isLoggedIn() {
    return !!getToken();
  }
  function getCachedUser() {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }
  function setCachedUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  async function api(path, options = {}) {
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      options.headers || {}
    );
    const token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;

    const res = await fetch(BC_CONFIG.API_BASE + path, {
      ...options,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (res.status === 401) {
      clearSession();
      renderAuthUI();
    }

    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      /* body bo'sh bo'lishi mumkin */
    }
    if (!res.ok) {
      const message = (data && data.error) || "Server xatosi (" + res.status + ")";
      throw new Error(message);
    }
    return data;
  }

  // ── TOAST ────────────────────────────────────────────────────────────
  function toast(message, type = "success", duration = 3200) {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      document.body.appendChild(stack);
    }
    const el = document.createElement("div");
    el.className = "toast " + type;
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(() => el.remove(), duration);
  }

  // ── TELEGRAM LOGIN WIDGET CALLBACK ──────────────────────────────────
  // Telegram widget global oynada "onTelegramAuth" nomli funksiyani chaqiradi.
  window.onTelegramAuth = async function (tgUser) {
    try {
      const result = await api("/api/auth/telegram", {
        method: "POST",
        body: tgUser,
      });
      setToken(result.token);
      const profile = await api("/api/auth/me");
      setCachedUser(profile);
      toast("Xush kelibsiz, " + profile.first_name + "!", "success");
      renderAuthUI();
      if (typeof window.onLoginSuccess === "function") {
        window.onLoginSuccess(profile);
      }
    } catch (e) {
      toast("Kirishda xato: " + e.message, "error");
    }
  };

  function logout() {
    clearSession();
    toast("Tizimdan chiqdingiz", "success");
    renderAuthUI();
    if (typeof window.onLogout === "function") window.onLogout();
  }

  // ── NAV BAR AUTH HOLATI ─────────────────────────────────────────────
  function renderAuthUI() {
    const slot = document.getElementById("authSlot");
    if (!slot) return;

    if (!isLoggedIn()) {
      slot.innerHTML = `<div id="tgLoginWidget"></div>`;
      mountTelegramWidget(document.getElementById("tgLoginWidget"));
      return;
    }

    const cached = getCachedUser();
    const coins = cached ? cached.coins : "…";
    const name = cached ? cached.first_name : "…";
    const initial = name && name[0] ? name[0].toUpperCase() : "?";
    const photo = cached && cached.photo_url;

    slot.innerHTML = `
      <div class="coin-pill">💰 <span id="navCoins">${coins}</span></div>
      <div class="avatar-chip" id="navAvatarBtn" title="${name}">
        ${
          photo
            ? `<img src="${photo}" alt="${name}">`
            : `<div class="fallback">${initial}</div>`
        }
      </div>
    `;
    const avatarBtn = document.getElementById("navAvatarBtn");
    if (avatarBtn) {
      avatarBtn.addEventListener("click", () => {
        window.location.href =
          "profile.html?id=" + (cached ? cached.user_id : "");
      });
    }

    // Fon rejimida haqiqiy profilni yangilab olamiz (coin o'zgargan bo'lishi mumkin)
    api("/api/auth/me")
      .then((profile) => {
        setCachedUser(profile);
        const coinEl = document.getElementById("navCoins");
        if (coinEl) coinEl.textContent = profile.coins;
      })
      .catch(() => {});
  }

  function mountTelegramWidget(container) {
    if (!container) return;
    container.innerHTML = "";
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", BC_CONFIG.BOT_USERNAME);
    script.setAttribute("data-size", "medium");
    script.setAttribute("data-radius", "8");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    container.appendChild(script);
  }

  // ── FORMAT YORDAMCHILARI ────────────────────────────────────────────
  function formatCoins(n) {
    return Number(n).toLocaleString("uz-UZ", { maximumFractionDigits: 1 });
  }
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }
  function timeAgo(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr.replace(" ", "T"));
    const diffMs = Date.now() - d.getTime();
    const days = Math.floor(diffMs / 86400000);
    if (days < 1) return "bugun";
    if (days === 1) return "kecha";
    if (days < 30) return days + " kun oldin";
    const months = Math.floor(days / 30);
    return months + " oy oldin";
  }

  return {
    api,
    toast,
    logout,
    isLoggedIn,
    getCachedUser,
    setCachedUser,
    renderAuthUI,
    formatCoins,
    escapeHtml,
    timeAgo,
    getToken,
  };
})();

document.addEventListener("DOMContentLoaded", () => {
  BC.renderAuthUI();
});
