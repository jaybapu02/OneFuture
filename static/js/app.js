// OneFuture - small helpers (no framework required).

// Auto-dismiss success messages.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".alert-auto").forEach(function (alert) {
    setTimeout(function () {
      var instance = bootstrap.Alert.getOrCreateInstance(alert);
      instance.close();
    }, 4000);
  });
});