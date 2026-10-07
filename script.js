/**
 * Dog Unpacked — light progressive enhancement for the Kit signup form.
 * Form still works without JS via POST to Kit (app.kit.com).
 */
(function () {
  var form = document.getElementById("newsletter-form");
  var statusEl = document.getElementById("form-status");
  if (!form || !statusEl) return;

  form.addEventListener("submit", function () {
    statusEl.textContent = "Sending…";
    statusEl.className = "form-note";
  });
})();
