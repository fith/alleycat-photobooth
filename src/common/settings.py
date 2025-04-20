import os
import json
from .logit import log

# Constants
DATA_DIR = "/data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

def load_settings(force_reload=True):
    """Load settings from JSON file
    
    Args:
        force_reload (bool): If True, always read from disk. If False, may use cached values.
    """
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings
        except Exception as e:
            log(f"Error loading settings: {e}")
    return {}

def save_settings(settings):
    """Save settings to JSON file"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        log(f"Error saving settings: {e}")
        return False