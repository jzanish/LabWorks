# constraint_editor/manager.py

import json
import os

# Example constraint schema definitions:
# We'll define some known "types" of constraints,
# and each type might require certain fields.
# This is a minimal example; you can expand as needed.
CONSTRAINT_SCHEMAS = {
    "max_per_week": {
        "fields_required": ["shift_name", "limit"]
    },
    "no_back_to_back": {
        "fields_required": ["shifts"]
    },
    "kl_preference": {
        "fields_required": ["ebus_min", "clerical_min", "gyn_min"]
    },
    # etc...
}


class ConstraintsManager:
    """
    Manages user-defined constraints such as "max_per_week for a shift," "no_back_to_back," etc.
    Stores them in a JSON file for persistence.
    Also provides conflict detection, schema validation, etc.
    """

    def __init__(self, staff_manager, shift_manager, constraints_file='data/constraints.json'):
        """
        :param staff_manager: reference to the StaffManager
        :param shift_manager: reference to the ShiftManager
        :param constraints_file: path to a JSON file that stores constraints
        """
        self.staff_manager = staff_manager
        self.shift_manager = shift_manager
        self.constraints_file = constraints_file
        self.constraints_data = []  # The in-memory list/dict of constraints

        self.load_data()

    def load_data(self):
        """Load constraints from JSON if available."""
        if os.path.isfile(self.constraints_file):
            try:
                with open(self.constraints_file, 'r') as f:
                    self.constraints_data = json.load(f)
            except json.JSONDecodeError:
                print(f"WARNING: Could not decode JSON from {self.constraints_file}; starting empty.")
                self.constraints_data = []
            except Exception as e:
                print(f"ERROR: Failed to load constraints from {self.constraints_file}: {e}")
                self.constraints_data = []
        else:
            self.constraints_data = []

    def save_data(self):
        """Save constraints to JSON."""
        try:
            with open(self.constraints_file, 'w') as f:
                json.dump(self.constraints_data, f, indent=4)
            print(f"DEBUG: Constraints saved to {self.constraints_file}")
        except Exception as e:
            print(f"ERROR: Could not save constraints: {e}")

    def list_constraints(self):
        """Return the entire constraints list."""
        return self.constraints_data

    def add_constraint(self, constraint_dict):
        """
        Add a new constraint after validating. If valid, append and save.
        :param constraint_dict: e.g. {"type": "no_back_to_back", "shifts": ["Cyto EUS", "Cyto FNA"]}
        :return: (bool, error_message) -> indicates success/failure and an optional error message
        """
        ok, err = self.validate_constraint(constraint_dict)
        if not ok:
            return False, err

        # Optional: check conflict
        conflict_msg = self.detect_conflict(constraint_dict)
        if conflict_msg:
            # Let user decide if it's a hard error or a warning.
            # We'll treat it as a warning here:
            print(f"WARNING: {conflict_msg}")

        self.constraints_data.append(constraint_dict)
        self.save_data()
        return True, None

    def remove_constraint(self, index):
        """Remove by index from constraints_data."""
        if 0 <= index < len(self.constraints_data):
            del self.constraints_data[index]
            self.save_data()

    def update_constraint(self, index, new_data):
        """Update an existing constraint in place."""
        if 0 <= index < len(self.constraints_data):
            # We'll re-validate with the updated data
            updated_dict = dict(self.constraints_data[index])  # copy
            updated_dict.update(new_data)

            ok, err = self.validate_constraint(updated_dict)
            if not ok:
                return False, err

            # Optionally check conflict again
            conflict_msg = self.detect_conflict(updated_dict)
            if conflict_msg:
                print(f"WARNING: {conflict_msg}")

            self.constraints_data[index] = updated_dict
            self.save_data()
            return True, None
        return False, "Index out of range"

    def validate_constraint(self, cdict):
        """
        Basic schema validation. If unknown 'type', or missing fields, return error.
        """
        ctype = cdict.get("type")
        if not ctype:
            return False, "Constraint has no 'type'."

        schema = CONSTRAINT_SCHEMAS.get(ctype)
        if not schema:
            return False, f"Unknown constraint type '{ctype}'."

        required_fields = schema.get("fields_required", [])
        for rf in required_fields:
            if rf not in cdict:
                return False, f"Constraint type '{ctype}' missing required field '{rf}'."

        # Additional validation logic if needed...
        return True, None

    def detect_conflict(self, cdict):
        """
        Example conflict check. E.g., if user sets 'max_per_week' for the same shift
        with two different limits. This is simplistic; you can expand as needed.
        """
        ctype = cdict.get("type")
        if ctype == "max_per_week":
            shift_name = cdict.get("shift_name")
            existing = [
                x for x in self.constraints_data
                if x.get("type") == "max_per_week" and x.get("shift_name") == shift_name
            ]
            if existing:
                return f"Multiple 'max_per_week' constraints found for shift '{shift_name}'."
        return None

    def find_constraints_by_type(self, constraint_type):
        """Helper to filter constraints by type."""
        return [c for c in self.constraints_data if c.get('type') == constraint_type]
