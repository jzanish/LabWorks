import json
import os

DEFAULT_EFFORT = 5  # fallback if not found

def load_effort_map(json_path="effort_map.json"):
    """
    Reads a JSON file that looks like:
    {
      "Monday": {"Cyto Nons 1": 5, "Cyto FNA": 8, ...},
      "Tuesday": { ... },
      ...
      "EBUS Friday": { ... },
      "Regular Friday": { ... }
    }
    Returns a dict, or an empty dict if file not found or invalid.
    """
    if not os.path.exists(json_path):
        print(f"Warning: no effort map file at {json_path}")
        return {}

    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                print(f"Warning: {json_path} did not contain a top-level JSON object/dict.")
                return {}
            return data
    except Exception as ex:
        print(f"Error loading {json_path}: {ex}")
        return {}
