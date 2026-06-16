// =========================================================
// ApexPay - js/register.js
// =========================================================

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("registerForm");
  const fullNameInput = document.getElementById("fullName");
  const emailInput = document.getElementById("email");
  const phoneInput = document.getElementById("phone");
  const passwordInput = document.getElementById("password");
  const termsInput = document.getElementById("terms");

  const nameErr = document.getElementById("nameErr");
  const emailErr = document.getElementById("emailErr");
  const phoneErr = document.getElementById("phoneErr");
  const passErr = document.getElementById("passErr");
  const termsErr = document.getElementById("termsErr");

  const strengthBar = document.getElementById("strengthBar");
  const strengthLabel = document.getElementById("strengthLabel");

  const submitBtn = form.querySelector('button[type="submit"]');

  // ---- Password strength meter ----
  passwordInput.addEventListener("input", () => {
    const val = passwordInput.value;
    const { score, label, color } = scorePassword(val);

    if (!strengthBar) return;
    strengthBar.style.width = `${(score / 4) * 100}%`;
    strengthBar.style.background = color;
    strengthLabel.textContent = val ? label : "";
    strengthLabel.style.color = color;
  });

  function scorePassword(val) {
    let score = 0;
    if (val.length >= 8) score++;
    if (val.length >= 12) score++;
    if (/[0-9]/.test(val) && /[A-Za-z]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;

    const levels = [
      { label: "Too weak", color: "#ef4444" },
      { label: "Weak", color: "#f59e0b" },
      { label: "Good", color: "#2563eb" },
      { label: "Strong", color: "#10b981" },
    ];
    const idx = Math.max(0, Math.min(score - 1, 3));
    return { score, ...(val ? levels[idx] : { label: "", color: "#e1e2ec" }) };
  }

  // ---- Submit ----
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    [nameErr, emailErr, phoneErr, passErr, termsErr].forEach((el) => (el.textContent = ""));

    const fullName = fullNameInput.value.trim();
    const email = emailInput.value.trim();
    const phone = phoneInput.value.trim();
    const password = passwordInput.value;

    let hasError = false;

    if (!fullName) {
      nameErr.textContent = "Full name is required.";
      hasError = true;
    }
    if (!email) {
      emailErr.textContent = "Work email is required.";
      hasError = true;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      emailErr.textContent = "Enter a valid email address.";
      hasError = true;
    }
    if (!phone) {
      phoneErr.textContent = "Phone number is required.";
      hasError = true;
    }
    if (!password) {
      passErr.textContent = "Password is required.";
      hasError = true;
    } else if (password.length < 8) {
      passErr.textContent = "Password must be at least 8 characters.";
      hasError = true;
    }
    if (!termsInput.checked) {
      termsErr.textContent = "You must agree to the Terms of Service and Privacy Policy.";
      hasError = true;
    }

    if (hasError) return;

    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = "Creating account...";

    try {
      const data = await Api.post("/auth/register", { fullName, email, phone, password });
      Auth.setSession(data);
      window.location.href = "dashboard.html";
    } catch (err) {
      if (err.status === 409) {
        emailErr.textContent = "An account with this email already exists.";
      } else if (err.data && err.data.error) {
        showToast(err.data.error, "error");
      } else {
        showToast("Something went wrong. Please try again.", "error");
      }
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  });
});
