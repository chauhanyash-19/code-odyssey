import re

def detect_voip_pattern(phone_number: str) -> dict:
    """
    Detects if a number is likely a VoIP or spoofed number based on Indian numbering patterns.
    Does NOT check GPS/live location. Just pure string pattern matching.
    """
    # Clean the number
    num = re.sub(r'\D', '', phone_number)
    
    # Strip +91 or 0
    if num.startswith('91') and len(num) > 10:
        num = num[2:]
    elif num.startswith('0') and len(num) > 10:
        num = num[1:]
        
    result = {
        'is_likely_voip': False,
        'confidence': 0.0,
        'reason': 'Matches standard mobile pattern'
    }
    
    if len(num) != 10:
        result['is_likely_voip'] = True
        result['confidence'] = 0.9
        result['reason'] = f'Invalid length for Indian mobile ({len(num)} digits)'
        return result
        
    # Check known VoIP/Virtual series (e.g. starting with 140 or specific +44 spoofing seen locally)
    if num.startswith('140'):
        result['is_likely_voip'] = True
        result['confidence'] = 0.95
        result['reason'] = 'Matches 140xxxxxxx telemarketing/bulk VoIP series'
        return result
        
    # Valid Indian mobiles start with 6, 7, 8, or 9
    if not re.match(r'^[6-9]', num):
        result['is_likely_voip'] = True
        result['confidence'] = 0.85
        result['reason'] = 'Does not start with valid mobile prefix (6-9)'
        return result
        
    return result
