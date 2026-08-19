from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    """Build a pagination URL that preserves the current query string."""
    request = context.get("request")
    params = request.GET.copy() if request else {}
    params["page"] = page_number
    return "?" + params.urlencode()


@register.filter
def get_item(mapping, key):
    """Look up a key in a dictionary from a template."""
    try:
        return mapping[key]
    except (KeyError, TypeError, IndexError):
        return None