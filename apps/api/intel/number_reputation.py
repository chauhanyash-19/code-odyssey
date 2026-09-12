import json
import os
import time

REPUTATION_FILE = os.path.join(os.path.dirname(__file__), 'reputation_store.json')

def _load_store() -> dict:
    if os.path.exists(REPUTATION_FILE):
        with open(REPUTATION_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def _save_store(store: dict):
    with open(REPUTATION_FILE, 'w') as f:
        json.dump(store, f, indent=2)

def get_reputation(phone_number: str) -> dict:
    """Returns the reputation record for a number."""
    store = _load_store()
    return store.get(phone_number, {
        'times_reported': 0,
        'last_flagged_ts': None,
        'associated_dossier_ids': [],
        'verdict_history': []
    })

def report_number(phone_number: str, dossier_id: str = None, verdict: str = 'CRITICAL'):
    """Increments the report count and saves history."""
    store = _load_store()
    record = store.get(phone_number, {
        'times_reported': 0,
        'last_flagged_ts': None,
        'associated_dossier_ids': [],
        'verdict_history': []
    })
    
    record['times_reported'] += 1
    record['last_flagged_ts'] = time.time()
    if dossier_id and dossier_id not in record['associated_dossier_ids']:
        record['associated_dossier_ids'].append(dossier_id)
    record['verdict_history'].append(verdict)
    
    store[phone_number] = record
    _save_store(store)
