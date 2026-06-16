// =========================================================
// ApexPay - js/landing.js
// =========================================================

document.addEventListener("DOMContentLoaded", () => {
  // ---- Animated stat counters (triggered on scroll into view) ----
  const statEls = document.querySelectorAll(".stat-num[data-count]");

  const animateCount = (el) => {
    const target = parseFloat(el.dataset.count);
    const prefix = el.dataset.prefix || "";
    const suffix = el.dataset.suffix || "";
    const isDecimal = String(target).includes(".");
    const duration = 1400;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const value = target * eased;

      const display = isDecimal ? value.toFixed(1) : Math.round(value).toLocaleString("en-US");
      el.textContent = `${prefix}${display}${suffix}`;

      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  };

  if (statEls.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            animateCount(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.4 }
    );

    statEls.forEach((el) => observer.observe(el));
  }
});
