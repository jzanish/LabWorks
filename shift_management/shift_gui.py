# shift_management/shift_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from shift_management.manager import ShiftManager

class ShiftTab:
    def __init__(self, parent_frame, shift_manager: ShiftManager):
        """
        GUI for managing shifts.
        """
        self.parent_frame = parent_frame
        self.shift_manager = shift_manager

        # This list will store which shift (or None) corresponds to each
        # listbox line, so we can match user selection to real shift objects.
        self.displayed_shifts = []

        self._create_gui()

    def _create_gui(self):
        # Frame for Shift List
        self.shift_list_frame = ttk.LabelFrame(self.parent_frame, text="Shifts")
        self.shift_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.shift_listbox = tk.Listbox(self.shift_list_frame, height=10)
        self.shift_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.scrollbar = ttk.Scrollbar(self.shift_list_frame, orient="vertical", command=self.shift_listbox.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.shift_listbox.config(yscrollcommand=self.scrollbar.set)

        # Button Frame
        self.button_frame = ttk.Frame(self.parent_frame)
        self.button_frame.pack(fill="x", padx=5, pady=5)

        self.add_button = ttk.Button(self.button_frame, text="Add Shift", command=self._open_add_shift_popup)
        self.edit_button = ttk.Button(self.button_frame, text="Edit Shift", command=self._open_edit_shift_popup)
        self.remove_button = ttk.Button(self.button_frame, text="Remove Shift", command=self._remove_shift)
        self.refresh_button = ttk.Button(self.button_frame, text="Refresh", command=self._refresh_shift_list)

        for btn in (self.add_button, self.edit_button, self.remove_button, self.refresh_button):
            btn.pack(side="left", padx=5, pady=5)

        self._refresh_shift_list()

    def _refresh_shift_list(self):
        """
        Populate the listbox with headings for each role, followed by each shift.
        We'll store a parallel list `self.displayed_shifts` so we know which lines
        are real shifts vs. headings or blank lines.
        """
        self.shift_listbox.delete(0, tk.END)
        self.displayed_shifts = []  # Reset the parallel list

        all_shifts = self.shift_manager.list_shifts()

        # Group shifts by role
        role_map = {}
        for shift_obj in all_shifts:
            role = shift_obj.role_required if shift_obj.role_required else "Any"
            role_map.setdefault(role, []).append(shift_obj)

        inserted_roles = set()

        # We'll iterate over all_shifts in the order they appear
        # so we keep your “no alphabetical” approach.
        for shift_obj in all_shifts:
            role = shift_obj.role_required if shift_obj.role_required else "Any"
            if role not in inserted_roles:
                # Insert a heading line
                self.shift_listbox.insert(tk.END, f"--- {role.upper()} ---")
                self.displayed_shifts.append(None)  # Heading => no shift

                inserted_roles.add(role)

                # Now insert each shift in that role
                for s in role_map[role]:
                    display_text = (
                        f"{s.name} | "
                        f"Flexible={s.is_flexible} | "
                        f"Open={s.can_remain_open} | "
                        f"Start={s.start_time} | "
                        f"End={s.end_time}"
                    )
                    self.shift_listbox.insert(tk.END, display_text)
                    # This line in the listbox corresponds to the real shift
                    self.displayed_shifts.append(s)

                # Insert a blank line
                self.shift_listbox.insert(tk.END, "")
                self.displayed_shifts.append(None)

    def _open_add_shift_popup(self):
        popup = tk.Toplevel(self.parent_frame)
        popup.title("Add Shift")

        tk.Label(popup, text="Shift Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        name_entry = tk.Entry(popup)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(popup, text="Role Required:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        role_values = ["Any", "Prep Staff", "Admin", "Cytologist"]
        role_combo = ttk.Combobox(popup, values=role_values)
        role_combo.current(0)
        role_combo.grid(row=1, column=1, padx=5, pady=5)

        is_flexible_var = tk.BooleanVar()
        tk.Checkbutton(popup, text="Flexible Shift", variable=is_flexible_var).grid(row=2, column=1, sticky="w")

        can_remain_open_var = tk.BooleanVar()
        tk.Checkbutton(popup, text="Can Remain Open", variable=can_remain_open_var).grid(row=3, column=1, sticky="w")

        tk.Label(popup, text="Start Time (HH:MM):").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        start_entry = tk.Entry(popup)
        start_entry.grid(row=4, column=1, padx=5, pady=5)

        tk.Label(popup, text="End Time (HH:MM):").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        end_entry = tk.Entry(popup)
        end_entry.grid(row=5, column=1, padx=5, pady=5)

        tk.Label(popup, text="Days of Week Needed:").grid(row=6, column=0, padx=5, pady=5, sticky="e")
        days_frame = ttk.Frame(popup)
        days_frame.grid(row=6, column=1, padx=5, pady=5, sticky="w")

        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days_vars = {}
        for day in days_list:
            var = tk.BooleanVar()
            cb = tk.Checkbutton(days_frame, text=day, variable=var)
            cb.pack(side="left")
            days_vars[day] = var

        def save_shift():
            name = name_entry.get().strip()
            role_req = role_combo.get().strip()
            is_flexible = is_flexible_var.get()
            can_remain_open = can_remain_open_var.get()
            start_time = start_entry.get().strip() or None
            end_time = end_entry.get().strip() or None

            if not name:
                messagebox.showerror("Validation Error", "Shift name is required.")
                return

            selected_days = [day for day, var in days_vars.items() if var.get()]

            self.shift_manager.add_shift(
                name=name,
                role_required=role_req,
                is_flexible=is_flexible,
                can_remain_open=can_remain_open,
                start_time=start_time,
                end_time=end_time,
                days_of_week=selected_days
            )
            self._refresh_shift_list()
            popup.destroy()

        tk.Button(popup, text="Add", command=save_shift).grid(row=7, column=1, pady=5)

    def _open_edit_shift_popup(self):
        selected_idx = self.shift_listbox.curselection()
        if not selected_idx:
            messagebox.showerror("Selection Error", "Please select a shift to edit.")
            return

        idx = selected_idx[0]
        shift_obj = self.displayed_shifts[idx]
        if shift_obj is None:
            messagebox.showerror("Selection Error", "Please select an actual shift, not a heading or blank line.")
            return

        # shift_obj is the real shift => open your edit popup
        popup = tk.Toplevel(self.parent_frame)
        popup.title("Edit Shift")

        tk.Label(popup, text="Shift Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        name_entry = tk.Entry(popup, width=25)
        name_entry.insert(0, shift_obj.name)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(popup, text="Role Required:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        role_values = ["Any", "Prep Staff", "Admin", "Cytologist"]
        role_combo = ttk.Combobox(popup, values=role_values)
        if shift_obj.role_required in role_values:
            role_combo.set(shift_obj.role_required)
        else:
            role_combo.current(0)
        role_combo.grid(row=1, column=1, padx=5, pady=5)

        is_flexible_var = tk.BooleanVar(value=shift_obj.is_flexible)
        tk.Checkbutton(popup, text="Flexible Shift", variable=is_flexible_var).grid(row=2, column=1, sticky="w")

        can_remain_open_var = tk.BooleanVar(value=shift_obj.can_remain_open)
        tk.Checkbutton(popup, text="Can Remain Open", variable=can_remain_open_var).grid(row=3, column=1, sticky="w")

        tk.Label(popup, text="Start Time (HH:MM):").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        start_entry = tk.Entry(popup, width=25)
        start_entry.insert(0, shift_obj.start_time or "")
        start_entry.grid(row=4, column=1, padx=5, pady=5)

        tk.Label(popup, text="End Time (HH:MM):").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        end_entry = tk.Entry(popup, width=25)
        end_entry.insert(0, shift_obj.end_time or "")
        end_entry.grid(row=5, column=1, padx=5, pady=5)

        # Days of Week
        tk.Label(popup, text="Days of Week Needed:").grid(row=6, column=0, padx=5, pady=5, sticky="e")
        days_frame = ttk.Frame(popup)
        days_frame.grid(row=6, column=1, padx=5, pady=5, sticky="w")

        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days_vars = {}
        for day in days_list:
            var = tk.BooleanVar(value=(day in getattr(shift_obj, 'days_of_week', [])))
            cb = tk.Checkbutton(days_frame, text=day, variable=var)
            cb.pack(side="left")
            days_vars[day] = var

        def save_edits():
            old_name = shift_obj.name
            new_name = name_entry.get().strip()
            new_role = role_combo.get().strip()
            new_is_flexible = is_flexible_var.get()
            new_can_remain_open = can_remain_open_var.get()
            new_start = start_entry.get().strip() or None
            new_end = end_entry.get().strip() or None

            selected_days = [day for day, var in days_vars.items() if var.get()]

            self.shift_manager.edit_shift(
                old_name,
                name=new_name,
                role_required=new_role,
                is_flexible=new_is_flexible,
                can_remain_open=new_can_remain_open,
                start_time=new_start,
                end_time=new_end,
                days_of_week=selected_days
            )
            self._refresh_shift_list()
            popup.destroy()

        tk.Button(popup, text="Save", command=save_edits).grid(row=7, column=1, pady=10)

    def _remove_shift(self):
        selected_idx = self.shift_listbox.curselection()
        if not selected_idx:
            messagebox.showerror("Selection Error", "Please select a shift to remove.")
            return

        idx = selected_idx[0]
        shift_obj = self.displayed_shifts[idx]
        if shift_obj is None:
            messagebox.showerror("Selection Error", "Please select an actual shift, not a heading or blank line.")
            return

        if messagebox.askyesno("Confirm Removal", f"Remove shift '{shift_obj.name}'?"):
            self.shift_manager.remove_shift(shift_obj.name)
            self._refresh_shift_list()
