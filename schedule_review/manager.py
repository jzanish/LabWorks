import os
import json
from datetime import datetime, timedelta

class ReviewManager:
    """
    Manages saved schedules for historical review, editing, and statistics.
    Schedules are stored as JSON files in `schedules_dir`.
    """

    def __init__(self, schedules_dir="data/schedules"):
        self.schedules_dir = schedules_dir
        os.makedirs(self.schedules_dir, exist_ok=True)

        # In-memory list of schedules (each an entire dict from the JSON)
        # We load them at startup; you can refresh or reload if needed.
        self.schedules = self._load_all_schedules()

    def _load_all_schedules(self):
        """
        Scan `schedules_dir`, load each *.json file, and return a list of schedule dicts.
        Each schedule dict is expected to have:
          {
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "assignments": {
               "YYYY-MM-DD": [
                  {"shift": "Cyto FNA", "assigned_to": "KEK", "role": "Cytologist"},
                  ...
               ],
               ...
            },
            "created_at": "...",
            "version": ...
            ... (any other metadata)
          }
        """
        all_schedules = []
        for fname in os.listdir(self.schedules_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.schedules_dir, fname)
                try:
                    with open(fpath, "r") as f:
                        data = json.load(f)
                        all_schedules.append(data)
                except Exception as e:
                    print(f"WARNING: Could not load schedule '{fname}': {e}")
        return all_schedules

    def list_schedules(self):
        """
        Returns the in-memory list of all schedules loaded.
        You could re-scan the directory if you want a real-time approach.
        """
        return self.schedules

    def commit_schedule(self, schedule_data):
        """
        Saves a new schedule to disk with a unique filename.
        The schedule_data should have at least 'start_date' and 'end_date'.
        We also insert a 'created_at' if missing, and a 'version' if desired.
        """
        start_date = schedule_data.get("start_date", "unknown")
        end_date = schedule_data.get("end_date", "unknown")

        # Add or update some metadata
        if "created_at" not in schedule_data:
            schedule_data["created_at"] = datetime.now().isoformat()
        if "version" not in schedule_data:
            # for versioning, you can store a numeric or a timestamp-based version
            schedule_data["version"] = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Example filename: "2025-01-10__2025-01-14__20231010_145200.json"
        filename = f"{start_date}__{end_date}__{schedule_data['version']}.json"
        fpath = os.path.join(self.schedules_dir, filename)

        # Write to disk
        with open(fpath, "w") as f:
            json.dump(schedule_data, f, indent=4)

        # Add to in-memory list
        self.schedules.append(schedule_data)

    def delete_schedule(self, index):
        """
        Remove a schedule from memory and optionally from disk if you want.
        For example, you can re-generate the filename from data and remove the file.
        """
        if index < 0 or index >= len(self.schedules):
            return False
        schedule_data = self.schedules[index]

        # Attempt to rebuild the file name and delete from disk
        start_date = schedule_data.get("start_date", "unknown")
        end_date = schedule_data.get("end_date", "unknown")
        version = schedule_data.get("version", "unknown")
        fname = f"{start_date}__{end_date}__{version}.json"
        fpath = os.path.join(self.schedules_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
        # remove from in-memory list
        self.schedules.pop(index)
        return True

    def update_schedule(self, index, new_data):
        """
        Overwrite an existing schedule in memory with 'new_data'.
        Then, optionally re-save to disk with the same filename or create a new version.
        """
        if index < 0 or index >= len(self.schedules):
            return

        old_data = self.schedules[index]
        # We'll keep the same version/filename for a "replace" approach:
        start_date = old_data.get("start_date", "unknown")
        end_date = old_data.get("end_date", "unknown")
        version = old_data.get("version", "unknown")

        # Overwrite in memory
        self.schedules[index] = new_data

        # Re-write to disk
        fname = f"{start_date}__{end_date}__{version}.json"
        fpath = os.path.join(self.schedules_dir, fname)
        with open(fpath, "w") as f:
            json.dump(new_data, f, indent=4)

    # ----------------------------------------------------------------------
    # ADVANCED STATISTICS
    # ----------------------------------------------------------------------
    def get_advanced_stats(self):
        """
        Return a dictionary or object with advanced stats:
         1) Staff usage across all schedules
         2) Who has or hasn't worked certain shifts in last X schedules
         3) Average # shifts per staff, etc.

        This example just shows usage_count for each (staff, shift).
        We'll add a few extras, like a staff-level total and staff who haven't done UTD.
        """
        usage_count = {}
        staff_shifts = {}  # staff -> set of shift names they worked
        all_staff = set()

        for sched in self.schedules:
            assignments = sched.get("assignments", {})
            for day, day_shifts in assignments.items():
                for rec in day_shifts:
                    shift_name = rec["shift"]
                    staff_init = rec["assigned_to"]
                    all_staff.add(staff_init)

                    # increment usage
                    usage_count[(staff_init, shift_name)] = usage_count.get((staff_init, shift_name), 0) + 1

                    # track distinct shift usage
                    if staff_init not in staff_shifts:
                        staff_shifts[staff_init] = set()
                    staff_shifts[staff_init].add(shift_name)

        # Identify staff who never worked "Cyto UTD"
        # or any other shift you care about
        staff_never_utd = []
        for stf in all_staff:
            # If stf not in staff_shifts, means they never worked any shift
            if (stf not in staff_shifts) or ("Cyto UTD" not in staff_shifts[stf]):
                staff_never_utd.append(stf)

        # Build the final stats structure
        stats = {
            "usage_count": usage_count,
            "staff_never_utd": staff_never_utd,
            "total_schedules": len(self.schedules),
        }
        # For more advanced stats, you could compute average # of shifts per staff, etc.
        return stats
