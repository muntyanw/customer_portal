from django import template
register = template.Library()

@register.filter(name="add_class")
def add_class(field, css):
    """Add CSS class to a form widget dynamically."""
    attrs = field.field.widget.attrs.copy()
    # merge classes if already present
    if "class" in attrs:
        attrs["class"] = (attrs["class"] + " " + css).strip()
    else:
        attrs["class"] = css
    return field.as_widget(attrs=attrs)


@register.filter(name="get_item")
def get_item(mapping, key):
    """
    Safely fetch a value from dict-like objects in templates.
    Returns None when key is missing or mapping is invalid.
    """
    try:
        return mapping.get(key)
    except Exception:
        return None
