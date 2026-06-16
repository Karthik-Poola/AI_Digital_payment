// =========================================================
// ApexPay - js/transfer.js
// =========================================================

document.addEventListener("DOMContentLoaded", () => {
  // ---- Elements ----
  const recipientInput = document.getElementById("recipientInput");
  const recipientErr = document.getElementById("recipientErr");
  const step1Btn = document.getElementById("step1Btn");

  const amountInput = document.getElementById("amountInput");
  const amountErr = document.getElementById("amountErr");
  const amountPreview = document.getElementById("amountPreview");
  const noteInput = document.getElementById("noteInput");
  const fraudBar = document.getElementById("fraudBar");
  const step2Btn = document.getElementById("step2Btn");
  const step2Back = document.getElementById("step2Back");

  const sumRecipient = document.getElementById("sumRecipient");
  const sumAmount = document.getElementById("sumAmount");
  const sumNote = document.getElementById("sumNote");
  const sumFee = document.getElementById("sumFee");
  const sumTotal = document.getElementById("sumTotal");
  const step3Btn = document.getElementById("step3Btn");
  const step3Back = document.getElementById("step3Back");

  const backDashBtn = document.getElementById("backDashBtn");
  const newTransferBtn = document.getElementById("newTransferBtn");

  const steps = {
    1: document.getElementById("step1"),
    2: document.getElementById("step2"),
    3: document.getElementById("step3"),
    success: document.getElementById("stepsuccess"),
  };

  const stepper = document.querySelector(".stepper");
  const stepNums = stepper ? stepper.querySelectorAll(".step-num") : [];
  const stepLabels = stepper ? stepper.querySelectorAll(".step-label") : [];

  // ---- State ----
  let selectedRecipient = null; // { name, identifier, userId, type }
  let isKnownRecipient = false;
  let isInternalTransfer = false;

  // ---- Prefill from dashboard "Quick Transfer" click ----
  const prefillName = sessionStorage.getItem("apexpay_prefill_recipient");
  if (prefillName) {
    recipientInput.value = prefillName;
    sessionStorage.removeItem("apexpay_prefill_recipient");
  }

  // ---- Contact chips (Step 1) ----
  document.querySelectorAll(".contact-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".contact-chip").forEach((c) => c.classList.remove("selected"));
      chip.classList.add("selected");
      recipientInput.value = chip.dataset.email || chip.dataset.name;
      recipientErr.textContent = "";
    });
  });

  // Load recent contacts from API and prepend to the contacts row
  loadRecentContacts();

  // ---- Step 1 -> 2 ----
  step1Btn.addEventListener("click", async () => {
    recipientErr.textContent = "";
    const value = recipientInput.value.trim();

    if (!value) {
      recipientErr.textContent = "Please enter a recipient.";
      return;
    }

    step1Btn.disabled = true;
    const original = step1Btn.textContent;
    step1Btn.textContent = "Looking up recipient...";

    try {
      const data = await Api.get(`/transfer/lookup?identifier=${encodeURIComponent(value)}`);
      selectedRecipient = data.recipient;
      selectedRecipient.type = data.type;
      isKnownRecipient = data.type === "contact";
      isInternalTransfer = data.type === "internal_user";

      goToStep(2);
    } catch (err) {
      recipientErr.textContent = err.message || "Couldn't look up recipient. Try again.";
    } finally {
      step1Btn.disabled = false;
      step1Btn.textContent = original;
    }
  });

  // ---- Quick amount buttons ----
  document.querySelectorAll(".quick-amount").forEach((btn) => {
    btn.addEventListener("click", () => {
      amountInput.value = btn.dataset.val;
      updatePreview();
      amountErr.textContent = "";
    });
  });

  amountInput.addEventListener("input", () => {
    updatePreview();
    amountErr.textContent = "";
  });

  function updatePreview() {
    const val = parseFloat(amountInput.value);
    amountPreview.textContent = isNaN(val) ? "$0.00" : `$${val.toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
  }

  // ---- Step 2 -> 3 (with fraud precheck) ----
  step2Btn.addEventListener("click", async () => {
    amountErr.textContent = "";
    const amount = parseFloat(amountInput.value);

    if (!amount || amount <= 0) {
      amountErr.textContent = "Enter a valid amount.";
      return;
    }
    if (amount > 50000) {
      amountErr.textContent = "Amount cannot exceed $50,000.";
      return;
    }

    step2Btn.disabled = true;
    fraudBar.style.display = "flex";
    fraudBar.querySelector(".fraud-status").textContent = "Checking...";
    fraudBar.classList.remove("ok", "warn", "blocked");

    try {
      const result = await Api.post("/transfer/precheck", {
        recipientIdentifier: selectedRecipient.identifier,
        amount,
        isKnownRecipient,
        isInternalTransfer,
      });

      const fraud = result.fraudCheck;

      if (result.blocked) {
        fraudBar.classList.add("blocked");
        fraudBar.querySelector(".fraud-status").textContent = `⛔ ${fraud.label}`;
        showToast("This transfer was flagged as high risk and cannot proceed.", "error");
        return; // stay on step 2
      }

      if (fraud.type === "warning") {
        fraudBar.classList.add("warn");
        fraudBar.querySelector(".fraud-status").textContent = `⚠️ ${fraud.label}`;
      } else {
        fraudBar.classList.add("ok");
        fraudBar.querySelector(".fraud-status").textContent = `✅ ${fraud.label}`;
      }

      setTimeout(() => goToStep(3), 500);
    } catch (err) {
      fraudBar.style.display = "none";
      showToast(err.message || "Couldn't run fraud check. Try again.", "error");
    } finally {
      step2Btn.disabled = false;
    }
  });

  step2Back.addEventListener("click", () => goToStep(1));

  // ---- Step 3: populate summary ----
  function populateSummary() {
    const amount = parseFloat(amountInput.value) || 0;
    const note = noteInput.value.trim();

    sumRecipient.textContent = selectedRecipient.name || selectedRecipient.identifier;
    sumAmount.textContent = `$${amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
    sumNote.textContent = note || "—";
    sumFee.textContent = "Free";
    sumTotal.textContent = `$${amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
  }

  step3Back.addEventListener("click", () => goToStep(2));

  // ---- Step 3 -> Execute ----
  step3Btn.addEventListener("click", async () => {
    const amount = parseFloat(amountInput.value);
    const note = noteInput.value.trim();

    step3Btn.disabled = true;
    const original = step3Btn.textContent;
    step3Btn.textContent = "Sending...";

    try {
      const result = await Api.post("/transfer/execute", {
        recipientName: selectedRecipient.name || selectedRecipient.identifier,
        recipientIdentifier: selectedRecipient.identifier,
        recipientUserId: selectedRecipient.userId || null,
        amount,
        note,
        saveContact: true,
      });

      if (!result.success) {
        const fraud = result.fraudCheck || {};
        showToast(fraud.label || "This transfer could not be completed.", "error");
        goToStep(2);
        return;
      }

      // Update cached user balance for other pages
      const user = Auth.getUser();
      if (user) {
        user.balance = result.newBalance;
        Auth.updateUser(user);
      }

      goToStep("success");
    } catch (err) {
      if (err.status === 400 && err.data && err.data.error === "Insufficient balance") {
        showToast("Insufficient balance for this transfer.", "error");
        goToStep(2);
      } else {
        showToast(err.message || "Transfer failed. Please try again.", "error");
      }
    } finally {
      step3Btn.disabled = false;
      step3Btn.textContent = original;
    }
  });

  // ---- Success panel actions ----
  backDashBtn.addEventListener("click", () => (window.location.href = "dashboard.html"));
  newTransferBtn.addEventListener("click", () => resetFlow());

  // ---- Step navigation ----
  function goToStep(step) {
    Object.values(steps).forEach((el) => {
      if (el) el.style.display = "none";
    });

    if (step === "success") {
      steps.success.style.display = "flex";
      return;
    }

    steps[step].style.display = "block";
    fraudBar.style.display = "none";

    if (step === 3) populateSummary();

    updateStepper(step);
  }

  function updateStepper(activeStep) {
    stepNums.forEach((el, idx) => {
      const stepNum = idx + 1;
      el.classList.remove("done", "active", "pending");
      if (stepNum < activeStep) el.classList.add("done");
      else if (stepNum === activeStep) el.classList.add("active");
      else el.classList.add("pending");

      // Show checkmark for completed steps
      el.textContent = stepNum < activeStep ? "✓" : stepNum;
    });

    stepLabels.forEach((el, idx) => {
      const stepNum = idx + 1;
      el.classList.remove("active", "pending", "done");
      if (stepNum === activeStep) el.classList.add("active");
      else if (stepNum < activeStep) el.classList.add("done");
      else el.classList.add("pending");
    });
  }

  function resetFlow() {
    selectedRecipient = null;
    isKnownRecipient = false;
    isInternalTransfer = false;

    recipientInput.value = "";
    amountInput.value = "";
    noteInput.value = "";
    amountPreview.textContent = "$0.00";
    recipientErr.textContent = "";
    amountErr.textContent = "";
    document.querySelectorAll(".contact-chip").forEach((c) => c.classList.remove("selected"));

    goToStep(1);
  }

  // ---- Load recent contacts ----
  async function loadRecentContacts() {
    try {
      const data = await Api.get("/transfer/contacts");
      const contacts = data.contacts || [];
      if (!contacts.length) return;

      const row = document.querySelector(".contacts-row");
      if (!row) return;

      row.innerHTML = contacts
        .map((c) => {
          const avatarContent = c.icon ? "🏢" : c.initials;
          return `
            <div class="contact-chip" data-name="${escapeAttr(c.name)}" data-email="${escapeAttr(c.identifier)}">
              <div class="chip-av" style="background:${c.bg || '#8b5cf6'}">${avatarContent}</div>
              <div class="chip-name">${escapeHtml(c.name)}</div>
            </div>
          `;
        })
        .join("");

      // Re-bind click handlers for newly rendered chips
      row.querySelectorAll(".contact-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          row.querySelectorAll(".contact-chip").forEach((c) => c.classList.remove("selected"));
          chip.classList.add("selected");
          recipientInput.value = chip.dataset.email || chip.dataset.name;
          recipientErr.textContent = "";
        });
      });
    } catch {
      // Non-critical -- keep static placeholder chips
    }
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function escapeAttr(str) {
    return escapeHtml(str).replace(/"/g, "&quot;");
  }

  // ---- Initial render ----
  updateStepper(1);
});
