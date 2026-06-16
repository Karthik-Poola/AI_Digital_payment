// =========================================================
// ApexPay - js/profile.js
// =========================================================

document.addEventListener("DOMContentLoaded", async () => {
  const profileAvatar = document.getElementById("profileAvatar");
  const profileName = document.getElementById("profileName");
  const profileRole = document.getElementById("profileRole");
  const profileEmail = document.getElementById("profileEmail");
  const profileBalance = document.getElementById("profileBalance");

  const profileForm = document.getElementById("profileForm");
  const fullNameInput = document.getElementById("fullName");
  const emailInput = document.getElementById("email");
  const phoneInput = document.getElementById("phone");
  const roleTitleInput = document.getElementById("roleTitle");
  const profileSaveStatus = document.getElementById("profileSaveStatus");
  const saveProfileBtn = document.getElementById("saveProfileBtn");

  const passwordForm = document.getElementById("passwordForm");
  const currentPasswordInput = document.getElementById("currentPassword");
  const newPasswordInput = document.getElementById("newPassword");
  const passwordErr = document.getElementById("passwordErr");
  const passwordSaveStatus = document.getElementById("passwordSaveStatus");
  const changePasswordBtn = document.getElementById("changePasswordBtn");

  const biometricToggle = document.getElementById("biometricToggle");
  const logoutBtnProfile = document.getElementById("logoutBtnProfile");

  if (logoutBtnProfile) {
    logoutBtnProfile.addEventListener("click", () => Auth.logout());
  }

  await loadProfile();

  // ---- Save profile info ----
  profileForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      fullName: fullNameInput.value.trim(),
      phone: phoneInput.value.trim(),
      roleTitle: roleTitleInput.value.trim(),
    };

    saveProfileBtn.disabled = true;
    const original = saveProfileBtn.textContent;
    saveProfileBtn.textContent = "Saving...";

    try {
      const data = await Api.put("/profile", payload);
      Auth.updateUser(data.user);
      applyUserData(data.user);
      showStatus(profileSaveStatus, "Saved!", false);
    } catch (err) {
      showStatus(profileSaveStatus, err.message || "Couldn't save changes.", true);
    } finally {
      saveProfileBtn.disabled = false;
      saveProfileBtn.textContent = original;
    }
  });

  // ---- Change password ----
  passwordForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    passwordErr.textContent = "";

    const currentPassword = currentPasswordInput.value;
    const newPassword = newPasswordInput.value;

    if (!currentPassword || !newPassword) {
      passwordErr.textContent = "Both fields are required.";
      return;
    }
    if (newPassword.length < 8) {
      passwordErr.textContent = "New password must be at least 8 characters.";
      return;
    }

    changePasswordBtn.disabled = true;
    const original = changePasswordBtn.textContent;
    changePasswordBtn.textContent = "Updating...";

    try {
      await Api.put("/profile/password", { currentPassword, newPassword });
      currentPasswordInput.value = "";
      newPasswordInput.value = "";
      showStatus(passwordSaveStatus, "Password updated!", false);
    } catch (err) {
      if (err.status === 401) {
        passwordErr.textContent = "Current password is incorrect.";
      } else {
        showStatus(passwordSaveStatus, err.message || "Couldn't update password.", true);
      }
    } finally {
      changePasswordBtn.disabled = false;
      changePasswordBtn.textContent = original;
    }
  });

  // ---- Biometric toggle ----
  biometricToggle.addEventListener("change", async () => {
    const enabled = biometricToggle.checked;
    try {
      const data = await Api.put("/profile/biometric", { enabled });
      const user = Auth.getUser();
      if (user) {
        user.biometricEnabled = data.biometricEnabled;
        Auth.updateUser(user);
      }
      showToast(
        data.biometricEnabled ? "Biometric login enabled." : "Biometric login disabled.",
        "success"
      );
    } catch (err) {
      biometricToggle.checked = !enabled; // revert
      showToast(err.message || "Couldn't update biometric setting.", "error");
    }
  });

  // ---------------------------------------------------
  async function loadProfile() {
    try {
      const data = await Api.get("/profile");
      Auth.updateUser(data.user);
      applyUserData(data.user);
    } catch (err) {
      showToast(err.message || "Couldn't load profile.", "error");
    }
  }

  function applyUserData(user) {
    profileAvatar.textContent = user.avatarInitials || "??";
    profileName.textContent = user.fullName || "—";
    profileRole.textContent = user.roleTitle || "Member";
    profileEmail.textContent = user.email || "—";
    profileBalance.textContent = `$${Number(user.balance || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

    fullNameInput.value = user.fullName || "";
    emailInput.value = user.email || "";
    phoneInput.value = user.phone || "";
    roleTitleInput.value = user.roleTitle || "";
    biometricToggle.checked = !!user.biometricEnabled;

    // Update avatar in topbar too
    document.querySelectorAll(".avatar").forEach((a) => (a.textContent = user.avatarInitials || "??"));
  }

  function showStatus(el, message, isError) {
    el.textContent = message;
    el.classList.toggle("error", isError);
    el.classList.add("show");
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove("show"), 2500);
  }
});
