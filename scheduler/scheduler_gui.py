import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import csv
import os
from datetime import datetime

SCHEDULER_ORDER_FILE = "data/scheduler_order.json"


class DualReorderDialog(tk.Toplevel):
    """
    A dialog that shows two lists side-by-side: staff on the left, shifts on the right.
    Each can be reordered with Up/Down. On OK, we call a callback with (new_staff_list, new_shift_list).
    """
    def __init__(self, parent, title, staff_items, shift_items, callback, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.title(title)
        self.callback = callback

        # Make a local copy so we can reorder them easily
        self.staff_list = list(staff_items)
        self.shift_list = list(shift_items)

        self._create_widgets()
        self._populate_listboxes()

    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left side: Staff
        staff_frame = ttk.LabelFrame(main_frame, text="Staff Order")
        staff_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.staff_listbox = tk.Listbox(staff_frame, selectmode=tk.SINGLE, width=30, height=15)
        self.staff_listbox.pack(side="left", fill="both", expand=True)

        btn_staff_frame = ttk.Frame(staff_frame)
        btn_staff_frame.pack(side="right", fill="y")

        up_staff_btn = ttk.Button(btn_staff_frame, text="Up", command=self._staff_move_up)
        up_staff_btn.pack(pady=5)
        down_staff_btn = ttk.Button(btn_staff_frame, text="Down", command=self._staff_move_down)
        down_staff_btn.pack(pady=5)

        # Right side: Shifts
        shift_frame = ttk.LabelFrame(main_frame, text="Shift Order")
        shift_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.shift_listbox = tk.Listbox(shift_frame, selectmode=tk.SINGLE, width=30, height=15)
        self.shift_listbox.pack(side="left", fill="both", expand=True)

        btn_shift_frame = ttk.Frame(shift_frame)
        btn_shift_frame.pack(side="right", fill="y")

        up_shift_btn = ttk.Button(btn_shift_frame, text="Up", command=self._shift_move_up)
        up_shift_btn.pack(pady=5)
        down_shift_btn = ttk.Button(btn_shift_frame, text="Down", command=self._shift_move_down)
        down_shift_btn.pack(pady=5)

        # Bottom: OK/Cancel
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", pady=5)
        ok_btn = ttk.Button(bottom_frame, text="OK", command=self._on_ok)
        ok_btn.pack(side="left", padx=10)
        cancel_btn = ttk.Button(bottom_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="right", padx=10)

    def _populate_listboxes(self):
        self.staff_listbox.delete(0, tk.END)
        for item in self.staff_list:
            self.staff_listbox.insert(tk.END, item)

        self.shift_listbox.delete(0, tk.END)
        for item in self.shift_list:
            self.shift_listbox.insert(tk.END, item)

    def _staff_move_up(self):
        sel = self.staff_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx <= 0:
            return
        self.staff_list[idx], self.staff_list[idx-1] = self.staff_list[idx-1], self.staff_list[idx]
        self._populate_listboxes()
        self.staff_listbox.select_set(idx-1)

    def _staff_move_down(self):
        sel = self.staff_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.staff_list)-1:
            return
        self.staff_list[idx], self.staff_list[idx+1] = self.staff_list[idx+1], self.staff_list[idx]
        self._populate_listboxes()
        self.staff_listbox.select_set(idx+1)

    def _shift_move_up(self):
        sel = self.shift_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx <= 0:
            return
        self.shift_list[idx], self.shift_list[idx-1] = self.shift_list[idx-1], self.shift_list[idx]
        self._populate_listboxes()
        self.shift_listbox.select_set(idx-1)

    def _shift_move_down(self):
        sel = self.shift_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.shift_list)-1:
            return
        self.shift_list[idx], self.shift_list[idx+1] = self.shift_list[idx+1], self.shift_list[idx]
        self._populate_listboxes()
        self.shift_listbox.select_set(idx+1)

    def _on_ok(self):
        # Return updated lists
        self.callback(self.staff_list, self.shift_list)
        self.destroy()


class SchedulerTab:
    def __init__(self, parent_frame, ortools_scheduler, staff_manager):
        self.parent_frame = parent_frame
        self.ortools_scheduler = ortools_scheduler
        self.staff_manager = staff_manager

        self.last_generated_schedule = None

        # We'll define a role order: for staff x day
        self.role_order = ["Cytologist", "Admin", "Prep Staff", "Unscheduled"]

        # Try loading staff/shift order from disk, if available
        self.staff_order, self.shift_order = self._load_orders_from_file()

        # Basic style config
        style = ttk.Style()
        style.configure("Treeview", font=("TkDefaultFont", 12))
        style.configure("Treeview.Heading", font=("TkDefaultFont", 12, "bold"), anchor="center")

        # SHIFT x Day on top
        self.bench_frame = ttk.LabelFrame(
            self.parent_frame, text="Shift-Based Assignments"
        )
        self.bench_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # STAFF x Day below
        self.role_frame = ttk.LabelFrame(
            self.parent_frame, text="Role-Based Schedule"
        )
        self.role_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Input & Export
        self._create_input_frame()
        self._create_export_buttons()
        self._create_reorder_button()

        # Merge staff from manager at init (keeps the staff_order mostly consistent)
        self._load_staff_order_from_manager()

    def _load_staff_order_from_manager(self):
        """
        Merge staff from manager into self.staff_order:
          - keep existing order for staff that still exist
          - remove staff who no longer exist
          - append newly found staff (alphabetical)
        """
        all_staff_objs = self.staff_manager.list_staff()
        all_inits = [s_obj.initials for s_obj in all_staff_objs]

        # remove old that no longer exist
        existing_in_self_order = [init for init in self.staff_order if init in all_inits]
        # newly added staff
        new_inits = sorted([init for init in all_inits if init not in existing_in_self_order])
        self.staff_order = existing_in_self_order + new_inits

    def _load_orders_from_file(self):
        """Load staff_order, shift_order from disk if available."""
        default_staff_order = [
            "LB", "KEK", "CAM", "CML", "TL", "NM", "CMM", "GN", "DS", "JZ", "HH", "CS", "AS", "XM", "MB", "EM", "CL",
            "KL", "LH", "TG", "TS"
        ]
        default_shift_order = [
            "Cyto Nons 1", "Cyto Nons 2", "Cyto FNA", "Cyto EUS", "Cyto FLOAT", "Cyto 2ND (1)", "Cyto 2ND (2)"
            "Cyto IMG", "Cyto APERIO", "Cyto MCY", "Cyto UTD", "Cyto UTD IMG",
            "Prep AM Nons", "Prep GYN", "Prep EBUS", "Prep FNA", "Prep NONS 1", "Prep NONS 2",
            "Prep Clerical"
        ]
        if not os.path.exists(SCHEDULER_ORDER_FILE):
            return (default_staff_order, default_shift_order)

        try:
            with open(SCHEDULER_ORDER_FILE, "r") as f:
                data = json.load(f)
            staff_order = data.get("staff_order", default_staff_order)
            shift_order = data.get("shift_order", default_shift_order)
            return (staff_order, shift_order)
        except Exception:
            # If something goes wrong, fallback
            return (default_staff_order, default_shift_order)

    def _save_orders_to_file(self):
        """Save self.staff_order, self.shift_order to disk."""
        data = {
            "staff_order": self.staff_order,
            "shift_order": self.shift_order
        }
        os.makedirs(os.path.dirname(SCHEDULER_ORDER_FILE), exist_ok=True)
        with open(SCHEDULER_ORDER_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def _create_input_frame(self):
        self.input_frame = ttk.Frame(self.parent_frame)
        self.input_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(self.input_frame, text="Start Date (YYYY-MM-DD):").grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )
        self.start_entry = tk.Entry(self.input_frame, width=12)
        self.start_entry.insert(0, "2024-01-01")
        self.start_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.input_frame, text="End Date (YYYY-MM-DD):").grid(
            row=0, column=2, padx=5, pady=5, sticky="e"
        )
        self.end_entry = tk.Entry(self.input_frame, width=12)
        self.end_entry.insert(0, "2024-01-07")
        self.end_entry.grid(row=0, column=3, padx=5, pady=5)

        self.gen_button = ttk.Button(self.input_frame, text="Generate Schedule", command=self.generate_schedule)
        self.gen_button.grid(row=0, column=4, padx=10, pady=5)

    def _create_export_buttons(self):
        self.export_frame = ttk.Frame(self.parent_frame)
        self.export_frame.pack(fill="x", padx=5, pady=5)

        export_json_btn = ttk.Button(self.export_frame, text="Export JSON", command=self._export_to_json)
        export_csv_btn = ttk.Button(self.export_frame, text="Export CSV", command=self._export_to_csv)

        export_json_btn.pack(side="left", padx=5)
        export_csv_btn.pack(side="left", padx=5)

    def _create_reorder_button(self):
        self.reorder_frame = ttk.Frame(self.parent_frame)
        self.reorder_frame.pack(fill="x", padx=5, pady=5)

        reorder_btn = ttk.Button(self.reorder_frame, text="Reorder Staff & Shifts", command=self._open_reorder_dialog)
        reorder_btn.pack(side="left", padx=5)

    def _open_reorder_dialog(self):
        """
        Single window with two side-by-side listboxes: staff on the left, shifts on the right.
        On OK -> staff_order, shift_order updated -> we also save them to disk + refresh schedule.
        """
        self._load_staff_order_from_manager()

        def reorder_callback(new_staff_list, new_shift_list):
            self.staff_order = new_staff_list
            self.shift_order = new_shift_list
            # Save to disk
            self._save_orders_to_file()
            messagebox.showinfo("Order Updated", "Staff & shift order updated successfully!")
            # Immediately refresh current schedule display
            self._refresh_schedule_display()

        DualReorderDialog(
            parent=self.parent_frame,
            title="Reorder Staff & Shifts",
            staff_items=self.staff_order,
            shift_items=self.shift_order,
            callback=reorder_callback
        )

    def generate_schedule(self):
        # Before generating, ensure staff ordering is up to date
        self._load_staff_order_from_manager()

        start_date_str = self.start_entry.get().strip()
        end_date_str = self.end_entry.get().strip()

        # Validate date
        try:
            s_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            e_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if e_date < s_date:
                raise ValueError("End date cannot be before start date.")
        except ValueError as ve:
            messagebox.showerror("Invalid Date", str(ve))
            return

        schedule_data = self.ortools_scheduler.generate_schedule(start_date_str, end_date_str)
        if not schedule_data:
            messagebox.showinfo("No Schedule", "No feasible solution or empty schedule.")
            return

        self.last_generated_schedule = schedule_data

        # Clear frames
        for w in self.bench_frame.winfo_children():
            w.destroy()
        for w in self.role_frame.winfo_children():
            w.destroy()

        # Build
        self._build_bench_table(schedule_data)
        self._build_role_table(schedule_data)

        messagebox.showinfo("Schedule Generated", "Schedule generated successfully!")

    def _refresh_schedule_display(self):
        """Re-draw the shift-based and role-based tables with the last known schedule using updated orders."""
        if not self.last_generated_schedule:
            return

        for w in self.bench_frame.winfo_children():
            w.destroy()
        for w in self.role_frame.winfo_children():
            w.destroy()

        self._build_bench_table(self.last_generated_schedule)
        self._build_role_table(self.last_generated_schedule)

    def _build_bench_table(self, schedule_data):
        """Shift x Day table shown on top."""
        day_list = self._date_range(schedule_data)

        # shift_map[shift][day] = staff
        shift_map = {}
        for day_str, assigns in schedule_data.items():
            for rec in assigns:
                shift_name = rec["shift"]
                staff_init = rec["assigned_to"]
                if shift_name not in shift_map:
                    shift_map[shift_name] = {}
                shift_map[shift_name][day_str] = staff_init

        columns = ["Shift"] + day_list
        tree = ttk.Treeview(self.bench_frame, columns=columns, show="headings")
        tree.pack(fill="both", expand=True)

        tree.heading("Shift", text="Shift", anchor="center")
        tree.column("Shift", width=150, anchor="w")

        # e.g. "Mon 01"
        for d in day_list:
            d_obj = datetime.strptime(d, "%Y-%m-%d")
            heading_text = d_obj.strftime("%a %d")
            tree.heading(d, text=heading_text, anchor="center")
            tree.column(d, width=100, anchor="center")

        # reorder shifts by self.shift_order
        shift_in_schedule = list(shift_map.keys())
        shift_ordered = [sh for sh in self.shift_order if sh in shift_in_schedule]
        leftover_shifts = [sh for sh in shift_in_schedule if sh not in shift_ordered]
        shift_ordered += leftover_shifts

        for sh_name in shift_ordered:
            if sh_name not in shift_map:
                continue
            day_dict = shift_map[sh_name]
            row_vals = [sh_name]
            for d in day_list:
                assigned = day_dict.get(d, "")
                assigned = "" if assigned == "Unassigned" else assigned
                row_vals.append(assigned)
            tree.insert("", "end", values=row_vals)

    def _build_role_table(self, schedule_data):
        """Staff x Day table, roles in order: Cytologist, Admin, Prep Staff, Unscheduled."""
        day_list = self._date_range(schedule_data)

        # role_map[role][staff][day] = shift
        role_map = {}

        # We'll also gather staff->role from manager so we can show unscheduled staff
        # even if they didn't appear in the schedule.
        all_staff_objs = self.staff_manager.list_staff()
        staff_role_map = {}
        for s_obj in all_staff_objs:
            # If role is not recognized, label them as "Unscheduled"
            r = s_obj.role if s_obj.role in ["Cytologist", "Admin", "Prep Staff"] else "Unscheduled"
            staff_role_map[s_obj.initials] = r

        # Gather all assigned staff from schedule
        for day_str, assigns in schedule_data.items():
            for rec in assigns:
                shift_name = rec["shift"]
                staff_init = rec["assigned_to"]
                if staff_init == "Unassigned":
                    continue
                # If role is from the schedule or from staff obj
                schedule_role = rec.get("role", None)
                # fallback to staff manager's role if schedule is missing role
                if not schedule_role or schedule_role == "Unknown":
                    schedule_role = staff_role_map.get(staff_init, "Unscheduled")

                if schedule_role not in role_map:
                    role_map[schedule_role] = {}
                if staff_init not in role_map[schedule_role]:
                    role_map[schedule_role][staff_init] = {}
                role_map[schedule_role][staff_init][day_str] = shift_name

        # Also ensure every staff is present at least once under their official role
        for s_init, r in staff_role_map.items():
            if r not in role_map:
                role_map[r] = {}
            if s_init not in role_map[r]:
                role_map[r][s_init] = {}  # no assigned days => empty

        columns = ["Staff"] + day_list
        tree = ttk.Treeview(self.role_frame, columns=columns, show="headings")
        tree.pack(fill="both", expand=True)

        tree.heading("Staff", text="Staff (Role)", anchor="center")
        tree.column("Staff", width=150, anchor="w")

        for d in day_list:
            d_obj = datetime.strptime(d, "%Y-%m-%d")
            heading_text = d_obj.strftime("%a %d")
            tree.heading(d, text=heading_text, anchor="center")
            tree.column(d, width=100, anchor="center")

        # reorder roles
        roles_in_schedule = list(role_map.keys())
        # keep them in self.role_order if present, else leftover at the end
        role_ordered = [r for r in self.role_order if r in roles_in_schedule]
        leftover_roles = [r for r in roles_in_schedule if r not in role_ordered]
        role_ordered += leftover_roles

        for role in role_ordered:
            tree.insert("", "end", values=[role] + ["" for _ in day_list], tags=("role_heading",))
            staff_map = role_map[role]

            # reorder staff by self.staff_order
            staff_in_this_role = list(staff_map.keys())
            staff_ordered = [init for init in self.staff_order if init in staff_in_this_role]
            leftover_staff = [init for init in staff_in_this_role if init not in staff_ordered]
            staff_ordered += leftover_staff

            for s_init in staff_ordered:
                day_dict = staff_map[s_init]
                row_vals = [s_init]
                for d in day_list:
                    shift_assigned = day_dict.get(d, "")
                    row_vals.append(shift_assigned)
                tree.insert("", "end", values=row_vals)

        tree.tag_configure("role_heading", font=("TkDefaultFont", 12, "bold"))

    def _export_to_json(self):
        if not self.last_generated_schedule:
            messagebox.showerror("Export Error", "No schedule available to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save Schedule as JSON"
        )
        if file_path:
            with open(file_path, "w") as f:
                json.dump(self.last_generated_schedule, f, indent=4)
            messagebox.showinfo("Export Success", f"Schedule exported to {file_path}")

    def _export_to_csv(self):
        if not self.last_generated_schedule:
            messagebox.showerror("Export Error", "No schedule available to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Schedule as CSV"
        )
        if file_path:
            with open(file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Shift", "Assigned To", "Role"])
                for day, assignments in self.last_generated_schedule.items():
                    for rec in assignments:
                        shift_name = rec["shift"]
                        assigned_to = rec["assigned_to"]
                        role = rec.get("role", "Any")
                        writer.writerow([day, shift_name, assigned_to, role])
            messagebox.showinfo("Export Success", f"Schedule exported to {file_path}")

    def _date_range(self, schedule_data):
        return sorted(schedule_data.keys(), key=lambda d: datetime.strptime(d, "%Y-%m-%d"))
