import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime
from io import StringIO


SCHEDULER_ORDER_FILE = "data/scheduler_order.json"
EBUS_FRIDAYS_FILE = "data/ebus_fridays.json"


class DualReorderDialog(tk.Toplevel):
    """
    Dialog for reordering staff & shifts side by side.
    """
    def __init__(self, parent, title, staff_items, shift_items, callback, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.title(title)
        self.callback = callback

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
        self.callback(self.staff_list, self.shift_list)
        self.destroy()


class ManualAssignmentDialog(tk.Toplevel):
    """
    A dialog for manually assigning staff to shifts in a day/shift grid.
    This version also pre-populates from existing preassignments.
    """
    def __init__(
        self,
        parent,
        title,
        day_list,
        shift_list,
        staff_list,
        callback,
        existing_preassigned=None,  # <--- new param to store old picks
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.title(title)
        self.callback = callback

        self.day_list = day_list
        self.shift_list = shift_list
        self.staff_list = staff_list

        # Keep track of existing picks
        self.existing_preassigned = existing_preassigned or {}

        self.cell_widgets = {}

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # row=0 => headings
        corner_lbl = ttk.Label(main_frame, text="Shift \\ Day")
        corner_lbl.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        for d_idx, d_str in enumerate(self.day_list):
            d_obj = datetime.strptime(d_str, "%Y-%m-%d")
            heading_text = d_obj.strftime("%a %d")
            lbl = ttk.Label(main_frame, text=heading_text, anchor="center")
            lbl.grid(row=0, column=d_idx+1, padx=5, pady=5, sticky="ew")

        for s_idx, shift_name in enumerate(self.shift_list):
            row_index = s_idx + 1
            shift_lbl = ttk.Label(main_frame, text=shift_name, anchor="w")
            shift_lbl.grid(row=row_index, column=0, padx=5, pady=5, sticky="w")

            for d_idx, d_str in enumerate(self.day_list):
                cb_var = tk.StringVar(value="None")
                cb = ttk.Combobox(
                    main_frame,
                    textvariable=cb_var,
                    values=["None"] + self.staff_list,
                    state="readonly",
                    width=10
                )
                cb.grid(row=row_index, column=d_idx+1, padx=5, pady=2, sticky="ew")
                self.cell_widgets[(d_str, shift_name)] = cb

        # Pre-populate combos with existing picks
        self._populate_existing_assignments()

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", pady=5)
        ok_btn = ttk.Button(bottom_frame, text="OK", command=self._on_ok)
        ok_btn.pack(side="left", padx=10)
        cancel_btn = ttk.Button(bottom_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="right", padx=10)

        total_cols = len(self.day_list) + 1
        for col in range(total_cols):
            main_frame.grid_columnconfigure(col, weight=1)

    def _populate_existing_assignments(self):
        """
        Fill each combobox with the staff initials from existing_preassigned.
        """
        for (d_str, shift_name), staff_init in self.existing_preassigned.items():
            if (d_str, shift_name) in self.cell_widgets:
                combo = self.cell_widgets[(d_str, shift_name)]
                # If staff_init not in combo's values, add it
                if staff_init not in combo['values'] and staff_init != "None":
                    current_vals = list(combo['values'])
                    current_vals.append(staff_init)
                    combo.config(values=current_vals)
                combo.set(staff_init)

    def _on_ok(self):
        preassigned = {}
        for (d_str, shift_name), combo in self.cell_widgets.items():
            chosen = combo.get()
            if chosen and chosen != "None":
                preassigned[(d_str, shift_name)] = chosen
        self.callback(preassigned)
        self.destroy()


class EbusFridayDialog(tk.Toplevel):
    """
    A dialog to manage which Fridays are considered EBUS Fridays.
    We store them in data/ebus_fridays.json (list of "YYYY-MM-DD" strings).
    """
    def __init__(self, parent, ebus_list, callback_save, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title("Manage EBUS Fridays")
        self.callback_save = callback_save
        self.ebus_dates = set(ebus_list)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        lbl = ttk.Label(main_frame, text="List of EBUS Fridays (YYYY-MM-DD):")
        lbl.pack(anchor="w")

        self.listbox = tk.Listbox(main_frame, height=8)
        self.listbox.pack(fill="both", expand=True, pady=5)
        for date_str in sorted(self.ebus_dates):
            self.listbox.insert(tk.END, date_str)

        entry_frame = ttk.Frame(main_frame)
        entry_frame.pack(fill="x", pady=5)
        self.new_date_var = tk.StringVar()
        entry = ttk.Entry(entry_frame, textvariable=self.new_date_var, width=12)
        entry.pack(side="left", padx=5)
        add_btn = ttk.Button(entry_frame, text="Add", command=self._on_add)
        add_btn.pack(side="left", padx=5)

        remove_btn = ttk.Button(main_frame, text="Remove Selected", command=self._on_remove)
        remove_btn.pack(pady=5)

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", pady=5)
        ok_btn = ttk.Button(bottom_frame, text="OK", command=self._on_ok)
        ok_btn.pack(side="left", padx=10)
        cancel_btn = ttk.Button(bottom_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="right", padx=10)

    def _on_add(self):
        date_str = self.new_date_var.get().strip()
        if not date_str:
            return
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid Date", "Date must be in YYYY-MM-DD format.")
            return
        if dt_obj.weekday() != 4:
            msg = "Warning: This date is not a Friday. Are you sure?"
            if not messagebox.askyesno("Non-Friday", msg):
                return
        if date_str not in self.ebus_dates:
            self.ebus_dates.add(date_str)
            self.listbox.insert(tk.END, date_str)
        self.new_date_var.set("")

    def _on_remove(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        date_str = self.listbox.get(idx)
        self.listbox.delete(idx)
        self.ebus_dates.discard(date_str)

    def _on_ok(self):
        final_list = sorted(self.ebus_dates)
        self.callback_save(final_list)
        self.destroy()


class SchedulerTab:
    def __init__(self, parent_frame, ortools_scheduler, staff_manager, review_manager=None):
        self.parent_frame = parent_frame
        self.ortools_scheduler = ortools_scheduler
        self.staff_manager = staff_manager
        self.review_manager = review_manager

        self.last_generated_schedule = None
        self.role_order = ["Cytologist", "Admin", "Prep Staff", "Unscheduled"]
        # This dictionary stores all manual picks => {(day_str, shift_name): "staff_initials"}
        self._preassigned = {}

        self.bench_tree = None
        self.role_tree = None

        self.staff_order, self.shift_order = self._load_orders_from_file()
        self.ebus_fridays = self._load_ebus_fridays()

        style = ttk.Style()
        style.configure("Treeview", font=("TkDefaultFont", 12))
        style.configure("Treeview.Heading", font=("TkDefaultFont", 12, "bold"), anchor="center")

        # SHIFT-based table
        self.bench_frame = ttk.LabelFrame(self.parent_frame, text="Shift-Based Assignments")
        self.bench_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # STAFF-based table
        self.role_frame = ttk.LabelFrame(self.parent_frame, text="Role-Based Schedule")
        self.role_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # 1) Input Frame
        self._create_input_frame()

        # 2) Another row of buttons for reorder/manual/ebus
        self.button_frame = ttk.Frame(self.parent_frame)
        self.button_frame.pack(fill="x", padx=5, pady=5)

        self._create_reorder_button(self.button_frame)
        self._create_manual_assign_button(self.button_frame)
        self._create_ebus_button(self.button_frame)

        # 3) Another row for SHIFT→Clipboard and STAFF→Clipboard
        self.export_frame = ttk.Frame(self.parent_frame)
        self.export_frame.pack(fill="x", padx=5, pady=5)

        shift_clip_btn = ttk.Button(self.export_frame, text="SHIFT → Clipboard", command=self._copy_bench_clipboard)
        staff_clip_btn = ttk.Button(self.export_frame, text="STAFF → Clipboard", command=self._copy_role_clipboard)
        shift_clip_btn.pack(side="left", padx=5)
        staff_clip_btn.pack(side="left", padx=5)

        # Merge staff from manager
        self._load_staff_order_from_manager()

    def _create_input_frame(self):
        self.input_frame = ttk.Frame(self.parent_frame)
        self.input_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(self.input_frame, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.start_entry = tk.Entry(self.input_frame, width=12)
        self.start_entry.insert(0, "2025-01-06")
        self.start_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.input_frame, text="End Date (YYYY-MM-DD):").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.end_entry = tk.Entry(self.input_frame, width=12)
        self.end_entry.insert(0, "2025-01-10")
        self.end_entry.grid(row=0, column=3, padx=5, pady=5)

        # "Generate Schedule" on the left
        gen_btn = ttk.Button(
            self.input_frame,
            text="Generate Schedule",
            command=self.generate_schedule
        )
        gen_btn.grid(row=0, column=4, padx=10, pady=5, sticky="w")

        # "Send to Schedule Review →" on the right
        review_btn = ttk.Button(self.input_frame, text="Send to Schedule Review →", command=self._on_send_to_review)
        review_btn.grid(row=0, column=5, padx=10, pady=5, sticky="e")

    # Manual Assignments
    def _create_manual_assign_button(self, parent):
        assign_btn = ttk.Button(parent, text="Manual Assignments", command=self._open_manual_dialog)
        assign_btn.pack(side="right", padx=5)

    def _open_manual_dialog(self):
        try:
            dt_s = datetime.strptime(self.start_entry.get().strip(), "%Y-%m-%d").date()
            dt_e = datetime.strptime(self.end_entry.get().strip(), "%Y-%m-%d").date()
            if dt_e < dt_s:
                raise ValueError("End date cannot be before start date.")
        except ValueError as ve:
            messagebox.showerror("Invalid Date", str(ve))
            return

        day_list = []
        one_day = (datetime(2020,1,2) - datetime(2020,1,1))
        cursor = dt_s
        while cursor <= dt_e:
            if cursor.weekday() < 5:
                day_list.append(cursor.strftime("%Y-%m-%d"))
            cursor += one_day

        all_shifts = self.ortools_scheduler.shift_manager.list_shifts()
        shift_name_map = {sh.name: sh for sh in all_shifts}
        shift_ordered = [sh for sh in self.shift_order if sh in shift_name_map]
        leftover_shifts = [sh for sh in shift_name_map.keys() if sh not in shift_ordered]
        final_shifts = shift_ordered + leftover_shifts

        staff_objs = self.staff_manager.list_staff()
        staff_inits = [s_obj.initials for s_obj in staff_objs]

        def on_ok(preassigned_dict):
            self._preassigned.update(preassigned_dict)
            messagebox.showinfo("Manual Assignments", "Your manual picks have been stored.")
            self.generate_schedule()

        ManualAssignmentDialog(
            parent=self.parent_frame,
            title="Manual Assignments",
            day_list=day_list,
            shift_list=final_shifts,
            staff_list=staff_inits,
            existing_preassigned=self._preassigned,
            callback=on_ok
        )

    # EBUS Fridays
    def _create_ebus_button(self, parent):
        ebus_btn = ttk.Button(parent, text="Manage EBUS Fridays", command=self._open_ebus_dialog)
        ebus_btn.pack(side="right", padx=5)

    def _open_ebus_dialog(self):
        def save_ebus_list(new_list):
            self.ebus_fridays = new_list
            self._save_ebus_fridays()
            messagebox.showinfo("EBUS Fridays Updated", "List of EBUS Fridays was updated and saved.")

        EbusFridayDialog(
            parent=self.parent_frame,
            ebus_list=self.ebus_fridays,
            callback_save=save_ebus_list
        )

    # SHIFT/STAFF Reorder
    def _create_reorder_button(self, parent):
        reorder_btn = ttk.Button(parent, text="Reorder Staff & Shifts", command=self._open_reorder_dialog)
        reorder_btn.pack(side="left", padx=5)

    def _open_reorder_dialog(self):
        self._load_staff_order_from_manager()

        def reorder_callback(new_staff_list, new_shift_list):
            self.staff_order = new_staff_list
            self.shift_order = new_shift_list
            self._save_orders_to_file()
            messagebox.showinfo("Order Updated", "Staff & shift order updated successfully!")
            self._refresh_schedule_display()

        DualReorderDialog(
            parent=self.parent_frame,
            title="Reorder Staff & Shifts",
            staff_items=self.staff_order,
            shift_items=self.shift_order,
            callback=reorder_callback
        )

    # Generate Schedule
    def generate_schedule(self):
        self._load_staff_order_from_manager()

        start_date_str = self.start_entry.get().strip()
        end_date_str = self.end_entry.get().strip()

        try:
            dt_s = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            dt_e = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if dt_e < dt_s:
                raise ValueError("End date cannot be before start date.")
        except ValueError as ve:
            messagebox.showerror("Invalid Date", str(ve))
            return

        # Check for EBUS Friday
        is_ebus_friday = False
        one_day = (datetime(2020,1,2) - datetime(2020,1,1))
        cursor = dt_s
        while cursor <= dt_e:
            if cursor.weekday() == 4:  # Friday
                if cursor.strftime("%Y-%m-%d") in self.ebus_fridays:
                    is_ebus_friday = True
                    break
            cursor += one_day

        schedule_data = self.ortools_scheduler.generate_schedule(
            start_date_str,
            end_date_str,
            preassigned=self._preassigned,
            is_ebus_friday=is_ebus_friday
        )
        if not schedule_data:
            messagebox.showinfo("No Schedule", "No feasible solution or empty schedule.")
            return

        self.last_generated_schedule = schedule_data

        for w in self.bench_frame.winfo_children():
            w.destroy()
        for w in self.role_frame.winfo_children():
            w.destroy()

        self._build_bench_table(schedule_data)
        self._build_role_table(schedule_data)

        self.last_generated_schedule = schedule_data

        messagebox.showinfo("Schedule Generated", "Schedule generated successfully!")

    def _on_send_to_review(self):
        if not self.last_generated_schedule:
            messagebox.showwarning("No Schedule", "Please generate a schedule before sending to review.")
            return

        start_date_str = self.start_entry.get().strip()
        end_date_str = self.end_entry.get().strip()

        schedule_data = {
            "start_date": start_date_str,
            "end_date": end_date_str,
            "assignments": self.last_generated_schedule,
            "created_at": datetime.now().isoformat()
        }

        if self.review_manager:
            self.review_manager.commit_schedule(schedule_data)
            messagebox.showinfo(
                "Schedule Review",
                "Schedule sent to review successfully!"
            )
        else:
            messagebox.showinfo(
                "Schedule Review",
                "No review_manager found—could not store the schedule."
            )

    def _refresh_schedule_display(self):
        self.generate_schedule()

    # SHIFT × DAY
    def _build_bench_table(self, schedule_data):
        self.bench_tree = None
        day_list = self._date_range(schedule_data)
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
        self.bench_tree = tree

        tree.heading("Shift", text="Shift", anchor="center")
        tree.column("Shift", width=150, anchor="w")

        for d in day_list:
            d_obj = datetime.strptime(d, "%Y-%m-%d")
            heading_text = d_obj.strftime("%a %d")
            tree.heading(d, text=heading_text, anchor="center")
            tree.column(d, width=100, anchor="center")

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

    # STAFF × DAY
    def _build_role_table(self, schedule_data):
        self.role_tree = None
        day_list = self._date_range(schedule_data)
        role_map = {}
        staff_role_map = {}

        all_staff_objs = self.staff_manager.list_staff()
        for s_obj in all_staff_objs:
            r = s_obj.role if s_obj.role in ["Cytologist", "Admin", "Prep Staff"] else "Unscheduled"
            staff_role_map[s_obj.initials] = r

        for day_str, assigns in schedule_data.items():
            for rec in assigns:
                shift_name = rec["shift"]
                staff_init = rec["assigned_to"]
                if staff_init == "Unassigned":
                    continue
                schedule_role = rec.get("role", None)
                if not schedule_role or schedule_role == "Unknown":
                    schedule_role = staff_role_map.get(staff_init, "Unscheduled")

                if schedule_role not in role_map:
                    role_map[schedule_role] = {}
                if staff_init not in role_map[schedule_role]:
                    role_map[schedule_role][staff_init] = {}
                role_map[schedule_role][staff_init][day_str] = shift_name

        for s_init, r in staff_role_map.items():
            if r not in role_map:
                role_map[r] = {}
            if s_init not in role_map[r]:
                role_map[r][s_init] = {}

        columns = ["Staff"] + day_list
        tree = ttk.Treeview(self.role_frame, columns=columns, show="headings")
        tree.pack(fill="both", expand=True)
        self.role_tree = tree

        tree.heading("Staff", text="Staff (Role)", anchor="center")
        tree.column("Staff", width=150, anchor="w")

        for d in day_list:
            d_obj = datetime.strptime(d, "%Y-%m-%d")
            heading_text = d_obj.strftime("%a %d")
            tree.heading(d, text=heading_text, anchor="center")
            tree.column(d, width=100, anchor="center")

        roles_in_schedule = list(role_map.keys())
        role_ordered = [r for r in self.role_order if r in roles_in_schedule]
        leftover_roles = [r for r in roles_in_schedule if r not in role_ordered]
        role_ordered += leftover_roles

        for role in role_ordered:
            tree.insert("", "end", values=[role] + ["" for _ in day_list], tags=("role_heading",))
            staff_map = role_map[role]
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

    def _treeview_to_list_of_lists(self, tree):
        if not tree:
            return []
        columns = tree["columns"]
        heading_row = [tree.heading(c)["text"] for c in columns]
        data = [heading_row]
        for child_id in tree.get_children(""):
            row_vals = tree.item(child_id)["values"]
            data.append(row_vals)
        return data

    def _copy_bench_clipboard(self):
        if not self.bench_tree:
            messagebox.showerror("No SHIFT Table", "No SHIFT x DAY table is present.")
            return
        data = self._treeview_to_list_of_lists(self.bench_tree)
        if len(data) < 2:
            messagebox.showwarning("Empty SHIFT Table", "SHIFT x DAY table is empty.")
            return

        output = StringIO()
        for row in data:
            line = "\t".join(str(v) for v in row)
            output.write(line + "\n")
        self.parent_frame.clipboard_clear()
        self.parent_frame.clipboard_append(output.getvalue())
        messagebox.showinfo("Copied", "SHIFT x DAY table copied to clipboard.\nPaste into Excel or similar.")

    def _copy_role_clipboard(self):
        if not self.role_tree:
            messagebox.showerror("No STAFF Table", "No STAFF x DAY table is present.")
            return
        data = self._treeview_to_list_of_lists(self.role_tree)
        if len(data) < 2:
            messagebox.showwarning("Empty STAFF Table", "STAFF x DAY table is empty.")
            return

        output = StringIO()
        for row in data:
            line = "\t".join(str(v) for v in row)
            output.write(line + "\n")
        self.parent_frame.clipboard_clear()
        self.parent_frame.clipboard_append(output.getvalue())
        messagebox.showinfo("Copied", "STAFF x DAY table copied to clipboard.\nPaste into Excel or similar.")

    def _date_range(self, schedule_data):
        return sorted(schedule_data.keys(), key=lambda d: datetime.strptime(d, "%Y-%m-%d"))

    def _load_staff_order_from_manager(self):
        all_staff_objs = self.staff_manager.list_staff()
        all_inits = [s_obj.initials for s_obj in all_staff_objs]
        existing_in_self_order = [init for init in self.staff_order if init in all_inits]
        new_inits = sorted([init for init in all_inits if init not in existing_in_self_order])
        self.staff_order = existing_in_self_order + new_inits

    def _load_orders_from_file(self):
        default_staff_order = [
            "LB", "KEK", "CAM", "CML", "TL", "NM", "CMM", "GN", "DS", "JZ", "HH", "CS", "AS", "XM", "MB", "EM", "CL",
            "KL", "LH", "TG", "TS"
        ]
        default_shift_order = [
            "Cyto Nons 1", "Cyto Nons 2", "Cyto FNA", "Cyto EUS", "Cyto FLOAT", "Cyto 2ND (1)", "Cyto 2ND (2)",
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
        except:
            return (default_staff_order, default_shift_order)

    def _save_orders_to_file(self):
        data = {"staff_order": self.staff_order, "shift_order": self.shift_order}
        os.makedirs(os.path.dirname(SCHEDULER_ORDER_FILE), exist_ok=True)
        with open(SCHEDULER_ORDER_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def _load_ebus_fridays(self):
        if not os.path.exists(EBUS_FRIDAYS_FILE):
            return []
        try:
            with open(EBUS_FRIDAYS_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except:
            return []

    def _save_ebus_fridays(self):
        os.makedirs(os.path.dirname(EBUS_FRIDAYS_FILE), exist_ok=True)
        with open(EBUS_FRIDAYS_FILE, "w") as f:
            json.dump(self.ebus_fridays, f, indent=4)

    # =========== Send to Schedule Review ===========
    def _on_send_to_review(self):
        if not self.last_generated_schedule:
            messagebox.showwarning("No Schedule", "Please generate a schedule before sending to review.")
            return

        # Build a schedule_data dict
        start_date_str = self.start_entry.get().strip()
        end_date_str = self.end_entry.get().strip()
        schedule_data = {
            "start_date": start_date_str,
            "end_date": end_date_str,
            "assignments": self.last_generated_schedule,
            "created_at": datetime.now().isoformat()
        }

        # The real commit call
        if self.review_manager:
            self.review_manager.commit_schedule(schedule_data)
            messagebox.showinfo(
                "Schedule Review",
                f"Schedule sent to review successfully! File saved for {start_date_str} → {end_date_str}."
            )
        else:
            messagebox.showerror(
                "No Review Manager",
                "No review_manager is attached to the SchedulerTab!"
            )

