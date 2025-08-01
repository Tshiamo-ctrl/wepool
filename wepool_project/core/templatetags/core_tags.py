# core/templatetags/core_tags.py
from django import template
from core.utils import get_referral_stats as get_stats_util  # Import with different name

register = template.Library()

@register.simple_tag
def get_referral_stats(profile):
    """Get referral statistics for a profile"""
    return get_stats_util(profile)  # Call the utility function, not itself

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return ''
