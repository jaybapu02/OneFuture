// OneFuture - small helpers (no framework required).

// Toast notifications: auto-dismiss, manual dismiss.
(function () {
  function dismiss(el) {
    if (!el) return;
    el.classList.add("toast-out");
    setTimeout(function () {
      el.remove();
    }, 320);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var toasts = document.querySelectorAll(".app-toast");
    toasts.forEach(function (toast) {
      setTimeout(function () {
        dismiss(toast);
      }, 5000);
    });

    document.querySelectorAll("[data-dismiss-toast]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        dismiss(btn.closest(".app-toast"));
      });
    });
  });

  // Dismiss toasts that arrive via HTMX swaps too.
  document.addEventListener("htmx:afterSwap", function (event) {
    event.target
      .querySelectorAll(".app-toast")
      .forEach(function (toast) {
        setTimeout(function () {
          dismiss(toast);
        }, 5000);
      });
  });
})();

// Keep the mobile sidebar offcanvas in sync with a tap on the backdrop.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".offcanvas-backdrop").forEach(function (backdrop) {
    backdrop.addEventListener("click", function () {
      document.querySelectorAll(".offcanvas.show").forEach(function (el) {
        bootstrap.Offcanvas.getInstance(el)?.hide();
      });
    });
  });
});

// Desktop sidebar collapse, with state persisted in localStorage.
(function () {
  var KEY = "of.sidebarCollapsed";

  function apply(state) {
    document.body.classList.toggle("sidebar-collapsed", state === "1");
    var btn = document.getElementById("sidebarToggle");
    if (!btn) return;
    var icon = btn.querySelector("i");
    if (state === "1") {
      icon.classList.remove("bi-chevron-left");
      icon.classList.add("bi-chevron-right");
    } else {
      icon.classList.remove("bi-chevron-right");
      icon.classList.add("bi-chevron-left");
    }
    btn.setAttribute("aria-expanded", String(state !== "1"));
  }

  document.addEventListener("DOMContentLoaded", function () {
    var saved = null;
    try {
      saved = localStorage.getItem(KEY);
    } catch (e) {
      saved = null;
    }
    apply(saved);

    var btn = document.getElementById("sidebarToggle");
    if (btn) {
      btn.addEventListener("click", function () {
        var collapsed = document.body.classList.toggle("sidebar-collapsed");
        try {
          localStorage.setItem(KEY, collapsed ? "1" : "0");
        } catch (e) {}
        apply(collapsed ? "1" : "0");
      });
    }
  });
})();