# shift_management/manager.py

import json
import os
from shift_management.shift import Shift

class ShiftManager:
    def __init__(self, data_file="data/shifts.json"):
        self.data_file = data_file
        self.shifts = self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 0:
            with open(self.data_file, "r") as f:
                data = json.load(f)
                return [Shift(**shift_info) for shift_info in data]
        return []

    def save_data(self):
        with open(self.data_file, "w") as f:
            json.dump([s.__dict__ for s in self.shifts], f, indent=4)

    def add_shift(self,
                  name,
                  role_required="Any",
                  is_flexible=False,
                  can_remain_open=False,
                  start_time=None,
                  end_time=None,
                  days_of_week=None):
        new_shift = Shift(
            name=name,
            role_required=role_required,
            is_flexible=is_flexible,
            can_remain_open=can_remain_open,
            start_time=start_time,
            end_time=end_time,
            days_of_week=days_of_week or []
        )
        self.shifts.append(new_shift)
        self.save_data()

    def edit_shift(self, old_name, **updates):
        for shift in self.shifts:
            if shift.name == old_name:
                for key, value in updates.items():
                    if hasattr(shift, key):
                        setattr(shift, key, value)
                self.save_data()
                return True
        return False

    def remove_shift(self, name):
        original_count = len(self.shifts)
        self.shifts = [s for s in self.shifts if s.name != name]
        if len(self.shifts) < original_count:
            self.save_data()
            return True
        return False

    def list_shifts(self):
        return self.shifts

    def get_shifts_for_role(self, role):
        return [s for s in self.shifts if s.role_required == role or s.role_required == "Any"]
