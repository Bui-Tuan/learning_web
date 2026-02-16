from django import template
register = template.Library()


@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return ''
    # Nếu key là int hoặc str đều được
    return dictionary.get(str(key)) or dictionary.get(int(key)) or ''
