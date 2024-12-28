# staff_management/staff_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
import json

class StaffTab:
    def __init__(self, parent_frame, staff_manager, shift_manager):
        """
        :param parent_frame: The frame or container in which this tab should be drawn.
        :param staff_manager: An instance of StaffManager.
        :param shift_manager: An instance of ShiftManager (for dynamic shift names).
        """
        self.parent_frame = parent_frame
        self.manager = staff_manager
        self.shift_manager = shift_manager

        # We'll store a parallel list so each line in the main listbox
        # corresponds to either a heading (None) or a real staff object.
        self.displayed_staff = []

        self.create_ui()
        self.populate_listbox()

    def create_ui(self):
        # Main Staff List
        self.staff_frame = ttk.LabelFrame(self.parent_frame, text="Staff List")
        self.staff_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.staff_listbox = tk.Listbox(self.staff_frame, height=8, width=80)
        self.staff_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.scrollbar = tk.Scrollbar(self.staff_frame)
        self.scrollbar.pack(side="right", fill="y")
        self.staff_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.staff_listbox.yview)

        # Buttons
        self.button_frame = ttk.Frame(self.parent_frame)
        self.button_frame.pack(fill="x", padx=10, pady=5)

        self.add_button = ttk.Button(self.button_frame, text="Add Staff", command=self.add_staff_popup)
        self.edit_button = ttk.Button(self.button_frame, text="Edit Selected", command=self.edit_selected_staff)
        self.remove_button = ttk.Button(self.button_frame, text="Remove Selected", command=self.remove_selected_staff)

        self.add_button.pack(side="left", padx=5)
        self.edit_button.pack(side="left", padx=5)
        self.remove_button.pack(side="left", padx=5)

    def populate_listbox(self):
        """Refresh the main staff listbox, grouping staff by role with headings."""
        self.staff_listbox.delete(0, tk.END)
        self.displayed_staff = []  # reset the parallel list

        staff_list = self.manager.list_staff()
        # 1) Group staff by role
        role_map = {}
        for s in staff_list:
            role_map.setdefault(s.role, []).append(s)

        # 2) Sort roles alphabetically
        sorted_roles = sorted(role_map.keys())

        for role in sorted_roles:
            # Insert a heading line
            self.staff_listbox.insert(tk.END, f"--- {role.upper()} ---")
            self.displayed_staff.append(None)  # heading => None

            # Sort staff by initials
            staff_for_role = sorted(role_map[role], key=lambda s: s.initials)

            for stf in staff_for_role:
                display_text = (
                    f"{stf.initials} | "
                    f"{stf.start_time}-{stf.end_time} | "
                    f"Shifts: {', '.join(stf.trained_shifts)} | "
                    f"Constraints: {stf.constraints}"
                )
                self.staff_listbox.insert(tk.END, display_text)
                self.displayed_staff.append(stf)  # real staff object

            # Optional blank line
            self.staff_listbox.insert(tk.END, "")
            self.displayed_staff.append(None)

    def get_selected_index(self):
        """Return the selected index in the main listbox, or None if nothing is selected."""
        selection = self.staff_listbox.curselection()
        if not selection:
            return None
        return selection[0]

    def add_staff_popup(self):
        popup = tk.Toplevel(self.parent_frame)
        popup.title("Add Staff")

        tk.Label(popup, text="Initials:").pack()
        initials_entry = tk.Entry(popup)
        initials_entry.pack()

        tk.Label(popup, text="Role:").pack()
        role_combobox = ttk.Combobox(popup, values=["Prep Staff", "Admin", "Cytologist"])
        role_combobox.current(0)
        role_combobox.pack()

        tk.Label(popup, text="Start Time (HH:MM):").pack()
        start_entry = tk.Entry(popup)
        start_entry.insert(0, "09:00")
        start_entry.pack()

        tk.Label(popup, text="End Time (HH:MM):").pack()
        end_entry = tk.Entry(popup)
        end_entry.insert(0, "17:00")
        end_entry.pack()

        # SHIFT SELECTION BY ROLE
        shifts_frame = ttk.Frame(popup)
        shifts_frame.pack(padx=5, pady=5, fill="x")

        cytolist_frame = ttk.LabelFrame(shifts_frame, text="Cytologist Shifts")
        cytolist_frame.pack(side="left", expand=True, fill="both", padx=5)
        cyto_listbox = tk.Listbox(cytolist_frame, selectmode="multiple", height=6)
        cyto_listbox.pack(fill="both", expand=True)

        preplist_frame = ttk.LabelFrame(shifts_frame, text="Prep Staff Shifts")
        preplist_frame.pack(side="left", expand=True, fill="both", padx=5)
        prep_listbox = tk.Listbox(preplist_frame, selectmode="multiple", height=6)
        prep_listbox.pack(fill="both", expand=True)

        adminlist_frame = ttk.LabelFrame(shifts_frame, text="Admin Shifts")
        adminlist_frame.pack(side="left", expand=True, fill="both", padx=5)
        admin_listbox = tk.Listbox(adminlist_frame, selectmode="multiple", height=6)
        admin_listbox.pack(fill="both", expand=True)

        all_shifts = self.shift_manager.list_shifts()
        for shift_obj in all_shifts:
            shift_name = shift_obj.name
            r = shift_obj.role_required
            if r == "Cytologist" or r == "Any":
                cyto_listbox.insert(tk.END, shift_name)
            if r == "Prep Staff" or r == "Any":
                prep_listbox.insert(tk.END, shift_name)
            if r == "Admin" or r == "Any":
                admin_listbox.insert(tk.END, shift_name)

        # Constraints + Half-Shift Admin
        tk.Label(popup, text="Constraints (JSON):").pack()
        constraints_entry = tk.Entry(popup)
        constraints_entry.insert(0, "{}")
        constraints_entry.pack()

        half_day_var = tk.BooleanVar(value=False)
        half_day_check = tk.Checkbutton(
            popup,
            text="Half-Shift Admin Cutoff",
            variable=half_day_var
        )
        half_day_check.pack()

        # Casual Status
        casual_var = tk.BooleanVar(value=False)
        casual_check = tk.Checkbutton(
            popup,
            text="Casual Status",
            variable=casual_var
        )
        casual_check.pack()

        def add_staff_action():
            initials = initials_entry.get().strip()
            role = role_combobox.get().strip()
            start_time = start_entry.get().strip()
            end_time = end_entry.get().strip()

            selected_cyto = [cyto_listbox.get(i) for i in cyto_listbox.curselection()]
            selected_prep = [prep_listbox.get(i) for i in prep_listbox.curselection()]
            selected_admin = [admin_listbox.get(i) for i in admin_listbox.curselection()]
            trained_shifts = selected_cyto + selected_prep + selected_admin

            constraints_raw = constraints_entry.get().strip()
            try:
                constraints_dict = json.loads(constraints_raw) if constraints_raw else {}
            except json.JSONDecodeError:
                messagebox.showerror("Invalid JSON", "Please enter valid JSON for constraints.")
                return

            constraints_dict["half_day_shift"] = half_day_var.get()

            if not initials:
                messagebox.showwarning("Missing Data", "Initials cannot be empty.")
                return

            # Debug: Print the trained_shifts being added
            print(f"DEBUG: Adding staff {initials} with trained_shifts: {trained_shifts}")

            self.manager.add_staff(
                initials=initials,
                start_time=start_time,
                end_time=end_time,
                role=role,
                trained_shifts=trained_shifts,
                constraints=constraints_dict,
                is_casual=casual_var.get()
            )
            self.populate_listbox()
            popup.destroy()

        ttk.Button(popup, text="Add Staff", command=add_staff_action).pack(pady=5)

    def edit_selected_staff(self):
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showwarning("No Selection", "Please select a staff member to edit.")
            return

        staff_obj = self.displayed_staff[idx]
        if staff_obj is None:
            messagebox.showerror("Selection Error", "Please select an actual staff, not a heading or blank line.")
            return

        popup = tk.Toplevel(self.parent_frame)
        popup.title(f"Edit Staff - {staff_obj.initials}")

        tk.Label(popup, text="Role:").pack()
        role_combobox = ttk.Combobox(popup, values=["Prep Staff", "Admin", "Cytologist"])
        if staff_obj.role in role_combobox["values"]:
            role_combobox.set(staff_obj.role)
        else:
            role_combobox.current(0)
        role_combobox.pack()

        tk.Label(popup, text="Start Time (HH:MM):").pack()
        start_entry = tk.Entry(popup)
        start_entry.insert(0, staff_obj.start_time)
        start_entry.pack()

        tk.Label(popup, text="End Time (HH:MM):").pack()
        end_entry = tk.Entry(popup)
        end_entry.insert(0, staff_obj.end_time)
        end_entry.pack()

        shifts_frame = ttk.Frame(popup)
        shifts_frame.pack(padx=5, pady=5, fill="x")

        # Cytologist
        cytolist_frame = ttk.LabelFrame(shifts_frame, text="Cytologist Shifts")
        cytolist_frame.pack(side="left", expand=True, fill="both", padx=5)
        cyto_listbox = tk.Listbox(cytolist_frame, selectmode="multiple", height=6)
        cyto_listbox.pack(fill="both", expand=True)

        # Prep Staff
        preplist_frame = ttk.LabelFrame(shifts_frame, text="Prep Staff Shifts")
        preplist_frame.pack(side="left", expand=True, fill="both", padx=5)
        prep_listbox = tk.Listbox(preplist_frame, selectmode="multiple", height=6)
        prep_listbox.pack(fill="both", expand=True)

        # Admin
        adminlist_frame = ttk.LabelFrame(shifts_frame, text="Admin Shifts")
        adminlist_frame.pack(side="left", expand=True, fill="both", padx=5)
        admin_listbox = tk.Listbox(adminlist_frame, selectmode="multiple", height=6)
        admin_listbox.pack(fill="both", expand=True)

        all_shifts = self.shift_manager.list_shifts()
        for shift_obj in all_shifts:
            shift_name = shift_obj.name
            r = shift_obj.role_required
            # Cytologist
            if r == "Cytologist" or r == "Any":
                size_before = cyto_listbox.size()
                cyto_listbox.insert(tk.END, shift_name)
                if shift_name in staff_obj.trained_shifts:
                    print(f"DEBUG: Selecting cytologist shift '{shift_name}' at index {size_before}")
                    cyto_listbox.selection_set(size_before, size_before)
            # Prep
            if r == "Prep Staff" or r == "Any":
                size_before = prep_listbox.size()
                prep_listbox.insert(tk.END, shift_name)
                if shift_name in staff_obj.trained_shifts:
                    print(f"DEBUG: Selecting prep shift '{shift_name}' at index {size_before}")
                    prep_listbox.selection_set(size_before, size_before)
            # Admin
            if r == "Admin" or r == "Any":
                size_before = admin_listbox.size()
                admin_listbox.insert(tk.END, shift_name)
                if shift_name in staff_obj.trained_shifts:
                    print(f"DEBUG: Selecting admin shift '{shift_name}' at index {size_before}")
                    admin_listbox.selection_set(size_before, size_before)

        tk.Label(popup, text="Other Constraints (JSON):").pack()
        constraints_entry = tk.Entry(popup)

        local_constraints = dict(staff_obj.constraints)
        half_day_var = tk.BooleanVar(value=local_constraints.get("half_day_shift", False))
        if "half_day_shift" in local_constraints:
            del local_constraints["half_day_shift"]

        constraints_entry.insert(0, json.dumps(local_constraints))
        constraints_entry.pack()

        half_day_check = tk.Checkbutton(
            popup,
            text="Half-Shift Admin Cutoff",
            variable=half_day_var
        )
        half_day_check.pack()

        # Casual Status
        casual_var = tk.BooleanVar(value=getattr(staff_obj, 'is_casual', False))
        casual_check = tk.Checkbutton(
            popup,
            text="Casual Status",
            variable=casual_var
        )
        casual_check.pack()

        def save_edits():
            new_role = role_combobox.get().strip()
            new_start = start_entry.get().strip()
            new_end = end_entry.get().strip()

            # gather new trained shifts
            sel_cyto = [cyto_listbox.get(i) for i in cyto_listbox.curselection()]
            sel_prep = [prep_listbox.get(i) for i in prep_listbox.curselection()]
            sel_admin = [admin_listbox.get(i) for i in admin_listbox.curselection()]
            new_trained_shifts = sel_cyto + sel_prep + sel_admin

            # Debug: Print the trained_shifts being edited
            print(f"DEBUG: Editing staff {staff_obj.initials} with new trained_shifts: {new_trained_shifts}")

            constraints_raw = constraints_entry.get().strip()
            try:
                updated_constraints = json.loads(constraints_raw) if constraints_raw else {}
            except json.JSONDecodeError:
                messagebox.showerror("Invalid JSON", "Please enter valid JSON for constraints.")
                return

            updated_constraints["half_day_shift"] = half_day_var.get()

            updated = self.manager.edit_staff(
                staff_obj.initials,
                role=new_role,
                start_time=new_start,
                end_time=new_end,
                trained_shifts=new_trained_shifts,
                constraints=updated_constraints,
                is_casual=casual_var.get()
            )
            if updated:
                self.populate_listbox()
                popup.destroy()
            else:
                messagebox.showerror("Update Failed", "Could not update staff.")

        ttk.Button(popup, text="Save Changes", command=save_edits).pack(pady=5)

    def remove_selected_staff(self):
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showwarning("No Selection", "Please select a staff member to remove.")
            return

        staff_obj = self.displayed_staff[idx]
        if staff_obj is None:
            messagebox.showerror("Selection Error", "Please select an actual staff, not a heading or blank line.")
            return

        if messagebox.askyesno("Confirm Removal", f"Remove staff '{staff_obj.initials}'?"):
            success = self.manager.remove_staff(staff_obj.initials)
            if success:
                self.populate_listbox()
            else:
                messagebox.showerror("Removal Error", "Could not remove staff.")
