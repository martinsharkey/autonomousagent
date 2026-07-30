import re

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if re.match(pattern, email):
        return True, ''
    return False, 'Invalid email format'

def validate_phone(phone):
    pattern = r'^\+?1?\d{10}$'
    if re.match(pattern, phone):
        return True, ''
    return False, 'Invalid phone number'

def validate_date(date_str):
    from datetime import datetime
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True, ''
    except ValueError:
        return False, 'Invalid date format (YYYY-MM-DD)'
