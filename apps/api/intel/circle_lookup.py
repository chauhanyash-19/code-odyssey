import re

# Small stub mapping for TRAI numbering series.
# In a real production build, this would be a full JSON/CSV dataset of all prefixes.
# THIS IS REGISTRATION CIRCLE ONLY, NOT CURRENT LOCATION.
_TRAI_SERIES = {
    "9810": {"circle": "Delhi NCR", "operator": "Airtel"},
    "9811": {"circle": "Delhi NCR", "operator": "Vodafone Idea"},
    "9820": {"circle": "Mumbai", "operator": "Vodafone Idea"},
    "9821": {"circle": "Mumbai", "operator": "Airtel"},
    "9945": {"circle": "Karnataka", "operator": "Airtel"},
    "9900": {"circle": "Karnataka", "operator": "Airtel"},
    "9830": {"circle": "Kolkata", "operator": "Airtel"},
    "9840": {"circle": "Tamil Nadu", "operator": "Airtel"},
    "7000": {"circle": "Madhya Pradesh", "operator": "Jio"},
    "1400": {"circle": "Telemarketing", "operator": "Bulk"},
}

def lookup_circle(phone_number: str) -> dict:
    """
    Looks up the registration telecom circle and operator for an Indian mobile number.
    NOTE: THIS REFLECTS ONLY WHERE THE NUMBER WAS ORIGINALLY ISSUED.
    IT DOES NOT REPRESENT THE CALLER'S CURRENT PHYSICAL LOCATION (GPS).
    """
    num = re.sub(r'\D', '', phone_number)
    
    if num.startswith('91') and len(num) > 10:
        num = num[2:]
    elif num.startswith('0') and len(num) > 10:
        num = num[1:]
        
    prefix = num[:4]
    
    record = _TRAI_SERIES.get(prefix)
    if record:
        return {
            "registration_circle": record["circle"],
            "operator": record["operator"],
            "note": "REGISTRATION CIRCLE, NOT CURRENT LOCATION"
        }
        
    return {
        "registration_circle": "Unknown / Not mapped",
        "operator": "Unknown",
        "note": "REGISTRATION CIRCLE, NOT CURRENT LOCATION"
    }
