# staff_management/manager.py

import json
import os
from staff_management.staff import Staff
from shift_management.manager import ShiftManager

class StaffManager:
    def __init__(self, data_file="data/staff.json", shift_manager: ShiftManager = None):
        """
        Manages staff profiles, storing them in JSON.
        :param data_file: Path to JSON for staff data.
        :param shift_manager: Optional ShiftManager to validate trained shifts.
        """
        self.data_file = data_file
        self.shift_manager = shift_manager  # needed to validate shift names if available
        self.staff_list = self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 0:
            with open(self.data_file, "r") as f:
                data = json.load(f)
                print(f"DEBUG: Loaded {len(data)} staff members from {self.data_file}")
                return [Staff(**item) for item in data]
        print(f"DEBUG: No existing staff data found in {self.data_file}. Starting with an empty list.")
        return []

    def save_data(self):
        with open(self.data_file, "w") as f:
            json.dump([s.__dict__ for s in self.staff_list], f, indent=4)
        print(f"DEBUG: Saved {len(self.staff_list)} staff members to {self.data_file}")

    def list_staff(self):
        return self.staff_list

    def add_staff(self,
                  initials,
                  start_time,
                  end_time,
                  role,
                  trained_shifts=None,
                  constraints=None,
                  is_casual=False):

        trained_shifts = trained_shifts or []

        # optional validation if shift_manager is present
        if self.shift_manager:
            valid_shift_names = [shift.name for shift in self.shift_manager.list_shifts()]
            for shift_name in trained_shifts:
                if shift_name not in valid_shift_names:
                    raise ValueError(f"Shift '{shift_name}' is not a valid shift.")

        new_staff = Staff(
            initials=initials,
            start_time=start_time,
            end_time=end_time,
            role=role,
            trained_shifts=trained_shifts,
            constraints=constraints or {},
            is_casual=is_casual
        )
        self.staff_list.append(new_staff)
        print(f"DEBUG: Added new staff: {new_staff}")
        self.save_data()

    def edit_staff(self, initials, **updates):
        for member in self.staff_list:
            if member.initials == initials:
                # handle trained_shifts validation
                if 'trained_shifts' in updates and self.shift_manager:
                    valid_shift_names = [s.name for s in self.shift_manager.list_shifts()]
                    for shift_name in updates['trained_shifts']:
                        if shift_name not in valid_shift_names:
                            raise ValueError(f"Shift '{shift_name}' is not valid.")
                if 'is_casual' in updates:
                    setattr(member, 'is_casual', updates['is_casual'])
                # apply updates
                for key, value in updates.items():
                    if hasattr(member, key):
                        setattr(member, key, value)
                print(f"DEBUG: Updated staff {initials} with {updates}")
                self.save_data()
                return True
        print(f"DEBUG: Staff {initials} not found for editing.")
        return False

    def remove_staff(self, initials):
        original_count = len(self.staff_list)
        self.staff_list = [s for s in self.staff_list if s.initials != initials]
        if len(self.staff_list) < original_count:
            self.save_data()
            print(f"DEBUG: Removed staff {initials}")
            return True
        print(f"DEBUG: Staff {initials} not found for removal.")
        return False

    def get_staff_by_role(self, role):
        return [s for s in self.staff_list if s.role == role]
