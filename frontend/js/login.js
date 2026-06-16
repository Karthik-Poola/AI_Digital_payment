// =========================================================
// ApexPay - js/login.js
// =========================================================

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const emailErr = document.getElementById("emailErr");
  const passErr = document.getElementById("passErr");
  const toggleBtn = document.getElementById("togglePass");
  const passkeyBtn = document.getElementById("passkeyBtn");
  const submitBtn = form.querySelector('button[type="submit"]');

  // Show / hide password
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const isPw = passwordInput.type === "password";
      passwordInput.type = isPw ? "text" : "password";
      toggleBtn.textContent = isPw ? "🙈" : "👁️";
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    emailErr.textContent = "";
    passErr.textContent = "";

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    let hasError = false;
    if (!email) {
      emailErr.textContent = "Email is required.";
      hasError = true;
    }
    if (!password) {
      passErr.textContent = "Password is required.";
      hasError = true;
    }
    if (hasError) return;

    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = "Signing in...";

    try {
      const data = await Api.post("/auth/login", { email, password });
      Auth.setSession(data);
      window.location.href = "dashboard.html";
    } catch (err) {
      if (err.status === 401) {
        passErr.textContent = "Invalid email or password.";
      } else {
        showToast(err.message || "Something went wrong. Please try again.", "error");
      }
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  });

  // Passkey / Biometrics
  if (passkeyBtn) {
    passkeyBtn.addEventListener("click", async () => {
      const email = emailInput.value.trim();
      if (!email) {
        emailErr.textContent = "Enter your email to use Passkey / Biometrics.";
        emailInput.focus();
        return;
      }
      passkeyBtn.disabled = true;
      const original = passkeyBtn.textContent;
      passkeyBtn.textContent = "🔑 Verifying...";

      try {
        const data = await Api.post("/auth/biometric-login", { email });
        Auth.setSession(data);
        window.location.href = "dashboard.html";
      } catch (err) {
        showToast(err.message || "Biometric login is not available for this account.", "error");
      } finally {
        passkeyBtn.disabled = false;
        passkeyBtn.textContent = original;
      }
    });
  }
});
