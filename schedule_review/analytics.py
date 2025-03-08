# analytics.py

import json
import os
from datetime import datetime
from scheduler.effort_map_loader import load_effort_map, DEFAULT_EFFORT

class ScheduleAnalytics:
    """
    Example analytics class that can:
      - sum weekly 'effort' by staff (calc_weekly_effort)
      - sum total SHIFT counts by staff (calc_shift_counts)
    Accepts an optional 'ebus_fridays' set if you need to treat some Fridays
    as 'EBUS Friday' vs 'Regular Friday' in the loaded effort map.
    """
    def __init__(self, ebus_fridays=None, effort_map_path="data/effort_map.json"):
        self.ebus_fridays = ebus_fridays or set()
        # Load your “effort map” from JSON (with fallback DEFAULT_EFFORT)
        self.effort_map = load_effort_map(effort_map_path)

    def calc_weekly_effort(self, schedule_data, included_shifts=None):
        """
        Summarizes total 'effort' by staff, grouped by ISO week number.

         - schedule_data: a dict with "assignments" => { "YYYY-MM-DD": [ {shift, assigned_to}, ... ] }
         - included_shifts: a set of shift names to filter by. If empty/None => all shifts.

        Returns: { iso_week_number -> { staff_init -> total_effort_points } }
        """
        if not schedule_data or "assignments" not in schedule_data:
            return {}
        if included_shifts is None:
            included_shifts = set()

        weekly_efforts = {}  # { iso_week -> { staff_init -> sum_effort } }
        assignments = schedule_data["assignments"]

        for day_str, rec_list in assignments.items():
            # parse day string -> date object
            try:
                day_dt = datetime.strptime(day_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            # iso_week
            iso_year, iso_week, iso_weekday = day_dt.isocalendar()

            # day_label for the loaded effort map
            if day_dt.weekday() == 4:  # Friday
                if day_str in self.ebus_fridays:
                    day_label = "EBUS Friday"
                else:
                    day_label = "Regular Friday"
            else:
                day_label = day_dt.strftime("%A")

            # sub-dict from your loaded effort map
            shift_eff_map = self.effort_map.get(day_label, {})

            # accumulate
            for rec in rec_list:
                shift_nm = rec.get("shift", "")
                stf_init = rec.get("assigned_to", "Unassigned")
                if stf_init == "Unassigned":
                    continue
                if included_shifts and (shift_nm not in included_shifts):
                    continue

                if iso_week not in weekly_efforts:
                    weekly_efforts[iso_week] = {}
                if stf_init not in weekly_efforts[iso_week]:
                    weekly_efforts[iso_week][stf_init] = 0

                shift_effort = shift_eff_map.get(shift_nm, DEFAULT_EFFORT)
                weekly_efforts[iso_week][stf_init] += shift_effort

        return weekly_efforts

    def calc_shift_counts(self, schedule_data, included_shifts=None):
        """
        Returns a dict { staff_init -> integer_count }, summing how many times staff
        worked any SHIFT in `included_shifts`. If included_shifts is empty => all shifts.
        """
        if not schedule_data or "assignments" not in schedule_data:
            return {}
        if included_shifts is None:
            included_shifts = set()

        staff_counts = {}
        assignments = schedule_data["assignments"]

        for day_str, rec_list in assignments.items():
            for rec in rec_list:
                shift_nm = rec.get("shift", "")
                stf_init = rec.get("assigned_to", "Unassigned")
                if stf_init == "Unassigned":
                    continue

                if included_shifts and (shift_nm not in included_shifts):
                    continue

                staff_counts[stf_init] = staff_counts.get(stf_init, 0) + 1

        return staff_counts
