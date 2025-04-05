import json
import os

CONFIG_FILE = "config.json"

def save_config(api_key, region, username=None, tagline=None):
    """Save configuration to a JSON file"""
    config = {
        "api_key": api_key,
        "region": region,
        "username": username,
        "tagline": tagline
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_config():
    """Load configuration from a JSON file"""
    if not os.path.exists(CONFIG_FILE):
        return None, "NA1", None, None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return (
                config.get("api_key"), 
                config.get("region", "NA1"), 
                config.get("username"),
                config.get("tagline")
            )
    except:
        return None, "NA1", None, None 