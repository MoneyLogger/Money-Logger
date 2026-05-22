from django import template

register = template.Library()

@register.filter(name='indian_currency')
def indian_currency(value):
    """
    Format number with Indian comma notation (lakhs, crores)
    Example: 1234567.89 -> 12,34,567.89
    """
    try:
        value = float(value)
        if '.' in str(value):
            int_part, dec_part = str(value).split('.')
        else:
            int_part = str(int(value))
            dec_part = '00'

        int_part = int_part.replace(',', '')

        is_negative = int_part.startswith('-')
        if is_negative:
            int_part = int_part[1:]

        int_part = int_part[::-1]

        result = []
        for i, digit in enumerate(int_part):
            if i == 3 or (i > 3 and (i - 3) % 2 == 0):
                result.append(',')
            result.append(digit)

        formatted = ''.join(result[::-1])

        if is_negative:
            formatted = '-' + formatted

        dec_part = dec_part[:2].ljust(2, '0')

        return f"{formatted}.{dec_part}"
    except (ValueError, TypeError):
        return value


@register.filter(name='currency')
def currency(value):
    return indian_currency(value)
