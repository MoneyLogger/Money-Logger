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
        # Split into integer and decimal parts
        if '.' in str(value):
            int_part, dec_part = str(value).split('.')
        else:
            int_part = str(int(value))
            dec_part = '00'
        
        # Remove any existing commas
        int_part = int_part.replace(',', '')
        
        # Handle negative numbers
        is_negative = int_part.startswith('-')
        if is_negative:
            int_part = int_part[1:]
        
        # Reverse the string for easier processing
        int_part = int_part[::-1]
        
        # Add commas: first after 3 digits, then after every 2 digits
        result = []
        for i, digit in enumerate(int_part):
            if i == 3 or (i > 3 and (i - 3) % 2 == 0):
                result.append(',')
            result.append(digit)
        
        # Reverse back
        formatted = ''.join(result[::-1])
        
        # Add negative sign if needed
        if is_negative:
            formatted = '-' + formatted
        
        # Ensure decimal part has 2 digits
        dec_part = dec_part[:2].ljust(2, '0')
        
        return f"{formatted}.{dec_part}"
    except (ValueError, TypeError):
        return value
