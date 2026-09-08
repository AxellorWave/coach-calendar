import json
import os
from app.config import STATE_FILE

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'last_id': 0}

def save_state(state: dict) -> None:
    dirname = os.path.dirname(STATE_FILE)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)
