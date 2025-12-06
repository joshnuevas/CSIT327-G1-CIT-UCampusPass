from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Usage: {{ my_dict|get_item:my_dynamic_key }}
    """
    return dictionary.get(key)