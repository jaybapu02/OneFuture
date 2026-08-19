"""Site-wide template context helpers."""
from django.conf import settings
from django.utils import timezone


def site_info(request):
    """Expose reusable site configuration to every template."""
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "OneFuture"),
        "today": timezone.localdate(),
    }
