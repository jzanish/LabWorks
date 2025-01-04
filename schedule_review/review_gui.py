import tkinter as tk
from tkinter import ttk, messagebox
import json
from datetime import datetime

class ScheduleReviewTab:
    """
    A GUI tab that displays a list of committed schedules (from ReviewManager),
    allows selecting one, and then 'View/Edit' in a combobox grid style.
    """
    def __init__(self, parent_frame, review_manager, staff_manager):
        """
        :param parent_frame: The frame (e.g., Notebook tab) for placing this UI.
        :param review_manager: An instance of ReviewManager.
        :param staff_manager: So we can get staff initials for the combos.
        """
        self.parent_frame = parent_frame
        self.review_manager = review_manager
        self.staff_manager = staff_manager

        self._create_ui()
        self._populate_schedule_list()

    def _create_ui(self):
        # Main area: list of schedules
        self.history_frame = ttk.LabelFrame(self.parent_frame, text="Saved Schedules")
        self.history_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.schedule_listbox = tk.Listbox(self.history_frame, height=10, width=80)
        self.schedule_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.scrollbar = ttk.Scrollbar(self.history_frame)
        self.scrollbar.pack(side="right", fill="y")
        self.schedule_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.schedule_listbox.yview)

        # Button row
        self.button_frame = ttk.Frame(self.parent_frame)
        self.button_frame.pack(fill="x", padx=5, pady=5)

        view_btn = ttk.Button(self.button_frame, text="View/Edit Schedule", command=self._edit_schedule)
        view_btn.pack(side="left", padx=5)

        del_btn = ttk.Button(self.button_frame, text="Delete", command=self._delete_schedule)
        del_btn.pack(side="left", padx=5)

        refresh_btn = ttk.Button(self.button_frame, text="Refresh List", command=self._populate_schedule_list)
        refresh_btn.pack(side="right", padx=5)

    def _populate_schedule_list(self):
        """
        Re-list all schedules from review_manager in the listbox.
        """
        self.schedule_listbox.delete(0, tk.END)
        schedules = self.review_manager.list_schedules()
        for i, sched in enumerate(schedules):
            start_date = sched.get("start_date", "unknown")
            end_date = sched.get("end_date", "unknown")
            version = sched.get("version", "")
            line = f"{start_date} -> {end_date} (v:{version})"
            self.schedule_listbox.insert(tk.END, line)

    def _get_selected_index(self):
        sel = self.schedule_listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a schedule from the list.")
            return None
        return sel[0]

    def _edit_schedule(self):
        idx = self._get_selected_index()
        if idx is None:
            return
        # get the schedule data
        sched_data = self.review_manager.list_schedules()[idx]

        # Open a new dialog
        ScheduleEditDialog(
            parent=self.parent_frame,
            schedule_data=sched_data,
            staff_manager=self.staff_manager,
            on_save=lambda updated: self._handle_schedule_save(idx, updated)
        )

    def _handle_schedule_save(self, index, updated_data):
        """
        Called after the user clicks 'OK' in the ScheduleEditDialog.
        We update the schedule in memory, and optionally re-save to disk.
        """
        self.review_manager.update_schedule(index, updated_data)
        messagebox.showinfo("Saved", "Schedule updated in review history.")
        self._populate_schedule_list()

    def _delete_schedule(self):
        idx = self._get_selected_index()
        if idx is None:
            return
        sure = messagebox.askyesno("Confirm", "Delete this schedule from review?")
        if sure:
            success = self.review_manager.delete_schedule(idx)
            if success:
                messagebox.showinfo("Deleted", "Schedule removed.")
                self._populate_schedule_list()

# ---------------------------------------------------------------------------
# The dialog for viewing/editing a single schedule using combos in a grid
# ---------------------------------------------------------------------------
class ScheduleEditDialog(tk.Toplevel):
    """
    A Toplevel that shows day columns, shift rows, and each cell is a combobox
    for staff initials, pre-filled from schedule_data.
    """
    def __init__(self, parent, schedule_data, staff_manager, on_save=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title("Edit Schedule (Combobox Grid)")
        self.schedule_data = schedule_data
        self.staff_manager = staff_manager
        self.on_save = on_save

        # We'll parse schedule_data to figure out day_list, shift_list, etc.
        # schedule_data["assignments"] is a dict => day -> list of {shift, assigned_to, ...}
        self.cell_widgets = {}  # (day, shift_name) -> combobox

        self._build_ui()

    def _build_ui(self):
        # parse days
        day_list = sorted(self.schedule_data.get("assignments", {}).keys())
        # parse shifts from the data itself
        # We'll gather all unique shift names that appear
        shift_set = set()
        for day_str in day_list:
            for rec in self.schedule_data["assignments"][day_str]:
                shift_set.add(rec["shift"])
        shift_list = sorted(list(shift_set))

        # We'll gather staff initials from staff_manager
        staff_inits = sorted([s.initials for s in self.staff_manager.list_staff()])

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # row=0 => day headings
        corner_lbl = ttk.Label(main_frame, text="Shift / Day")
        corner_lbl.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        for col_idx, day_str in enumerate(day_list, start=1):
            day_obj = datetime.strptime(day_str, "%Y-%m-%d")
            heading_text = day_obj.strftime("%a %d")
            lbl = ttk.Label(main_frame, text=heading_text, anchor="center")
            lbl.grid(row=0, column=col_idx, padx=5, pady=5, sticky="ew")

        # For each shift, we create a row
        for row_idx, shift_name in enumerate(shift_list, start=1):
            shift_lbl = ttk.Label(main_frame, text=shift_name, anchor="w")
            shift_lbl.grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")

            # For each day, we add a combobox
            for col_idx, day_str in enumerate(day_list, start=1):
                # find who is assigned to this shift on this day, if any
                assigned_staff = "None"
                for rec in self.schedule_data["assignments"][day_str]:
                    if rec["shift"] == shift_name:
                        assigned_staff = rec["assigned_to"]
                        break

                cb_var = tk.StringVar(value=assigned_staff if assigned_staff else "None")
                cb = ttk.Combobox(
                    main_frame,
                    textvariable=cb_var,
                    values=["None"] + staff_inits,
                    state="readonly",
                    width=10
                )
                cb.grid(row=row_idx, column=col_idx, padx=5, pady=2, sticky="ew")
                self.cell_widgets[(day_str, shift_name)] = cb

        # OK / Cancel
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", pady=5)
        ok_btn = ttk.Button(bottom_frame, text="OK", command=self._on_ok)
        ok_btn.pack(side="left", padx=10)
        cancel_btn = ttk.Button(bottom_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="right", padx=10)

        # Adjust column weights so combos expand
        total_cols = len(day_list) + 1
        for c in range(total_cols):
            main_frame.columnconfigure(c, weight=1)

    def _on_ok(self):
        """
        Build an updated 'schedule_data' from the combobox picks,
        then call on_save(updated_data).
        """
        updated_assignments = {}
        # We'll rebuild the day->listOfShifts structure
        day_list = sorted(self.schedule_data["assignments"].keys())
        shift_map = {}  # day_str -> shift_name -> assigned_to

        for (day_str, shift_name), combo in self.cell_widgets.items():
            chosen_staff = combo.get()
            # store in shift_map
            if day_str not in shift_map:
                shift_map[day_str] = {}
            shift_map[day_str][shift_name] = chosen_staff

        # Now convert shift_map to the same format as "assignments"
        # day_str -> [ {shift, assigned_to, role?, ...}, ... ]
        for day_str in day_list:
            day_recs = []
            for shift_name, assigned_staff in shift_map[day_str].items():
                day_recs.append({
                    "shift": shift_name,
                    "assigned_to": assigned_staff if assigned_staff != "None" else "Unassigned",
                    # If the schedule had role/is_flexible/can_remain_open, you can keep it if needed
                })
            updated_assignments[day_str] = day_recs

        new_data = dict(self.schedule_data)  # shallow copy
        new_data["assignments"] = updated_assignments

        if self.on_save:
            self.on_save(new_data)  # callback to parent's update logic
        self.destroy()
