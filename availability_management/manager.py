# availability_management/manager.py

import json
import os

class AvailabilityManager:
    def __init__(self, data_file="data/availability.json"):
        self.data_file = data_file
        self.availability_list = self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 0:
            with open(self.data_file, "r") as f:
                return json.load(f)
        return []

    def save_data(self):
        with open(self.data_file, "w") as f:
            json.dump(self.availability_list, f, indent=4)

    def list_availability(self):
        return self.availability_list

    def add_availability(self, initials, date, reason="PTO"):
        """
        A simple helper that creates a record marking staff 'initials' as unavailable on 'date'
        (by default reason="PTO", but you can store "Sick" or anything else).
        """
        record = {
            "initials": initials,
            "date": date,
            "reason": reason,
            "is_holiday": False
        }
        self.availability_list.append(record)
        self.save_data()

    def add_record(self, record):
        """
        A more generic approach. 'record' can be:
          {
            "initials": "ALL",
            "date": "2024-12-25",
            "reason": "Holiday",
            "is_holiday": true
          }
        or
          {
            "initials": "JD",
            "date": "2024-01-02",
            "reason": "PTO",
            "is_holiday": false
          }
        etc.
        This allows storing either holiday or staff unavailability in the same list.
        """
        self.availability_list.append(record)
        self.save_data()

    def remove_availability(self, initials, date):
        """
        Removes an unavailability record (PTO, Sick, etc.) for 'initials' on 'date'
        or a holiday record if initials="ALL" (or however you store it).
        """
        before = len(self.availability_list)
        self.availability_list = [
            rec for rec in self.availability_list
            if not (rec["initials"] == initials and rec["date"] == date)
        ]
        if len(self.availability_list) < before:
            self.save_data()
            return True
        return False

    def is_holiday(self, date_str):
        """
        Returns True if there's a record with 'is_holiday' = True for date_str,
        meaning NO staff should work that day.
        """
        for rec in self.availability_list:
            if rec.get("is_holiday", False) and rec.get("date") == date_str:
                return True
        return False

    def is_available(self, initials, date_str):
        """
        Default to True (staff is available),
        unless:
          1) There's a holiday record for date_str, or
          2) There's a record for this staff on that date (PTO, Sick, etc.)
        """
        # 1) If date_str is a holiday
        if self.is_holiday(date_str):
            return False

        # 2) If there's a record for this staff that says they're out
        for rec in self.availability_list:
            if rec["initials"] == initials and rec["date"] == date_str:
                # staff is unavailable for that date
                return False

        # 3) Otherwise, staff is default-available
        return True
