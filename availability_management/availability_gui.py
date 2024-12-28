# availability_management/availability_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
import json

class AvailabilityTab:
    def __init__(self, parent_frame, availability_manager, staff_manager):
        """
        Basic GUI for availability tracking.
        """
        self.parent_frame = parent_frame
        self.availability_manager = availability_manager
        self.staff_manager = staff_manager

        self.create_ui()
        self.populate_listbox()

    def create_ui(self):
        self.avail_frame = ttk.LabelFrame(self.parent_frame, text="Availability Records")
        self.avail_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.avail_listbox = tk.Listbox(self.avail_frame, height=10, width=80)
        self.avail_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.scrollbar = ttk.Scrollbar(self.avail_frame)
        self.scrollbar.pack(side="right", fill="y")
        self.avail_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.avail_listbox.yview)

        self.button_frame = ttk.Frame(self.parent_frame)
        self.button_frame.pack(fill="x", padx=10, pady=5)

        self.add_button = ttk.Button(self.button_frame, text="Add Availability", command=self.add_availability_popup)
        self.holiday_button = ttk.Button(self.button_frame, text="Add Holiday", command=self.add_holiday_popup)
        self.remove_button = ttk.Button(self.button_frame, text="Remove Selected", command=self.remove_selected_record)
        self.add_button.pack(side="left", padx=5)
        self.holiday_button.pack(side="left", padx=5)
        self.remove_button.pack(side="left", padx=5)

    def populate_listbox(self):
        self.avail_listbox.delete(0, tk.END)
        for rec in self.availability_manager.list_availability():
            line = f"{rec['initials']} | {rec['date']} | Reason: {rec['reason']}"
            self.avail_listbox.insert(tk.END, line)

    def add_availability_popup(self):
        popup = tk.Toplevel(self.parent_frame)
        popup.title("Add Availability")

        # 1) Get the list of staff from staff_manager
        staff_list = self.staff_manager.list_staff()
        # 2) Extract initials
        valid_initials = [s.initials for s in staff_list]

        tk.Label(popup, text="Staff Initials:").pack()
        staff_initials_combo = ttk.Combobox(
            popup,
            values=valid_initials,
            state="readonly"
        )
        if valid_initials:
            staff_initials_combo.current(0)  # default to first staff
        staff_initials_combo.pack()

        tk.Label(popup, text="Date (YYYY-MM-DD):").pack()
        date_entry = tk.Entry(popup)
        date_entry.pack()

        tk.Label(popup, text="Reason:").pack()
        reason_entry = tk.Entry(popup)
        reason_entry.insert(0, "PTO")
        reason_entry.pack()

        def add_avail_action():
            initials = staff_initials_combo.get().strip()
            date_str = date_entry.get().strip()
            reason = reason_entry.get().strip()

            if not initials or not date_str:
                messagebox.showerror("Validation Error", "Staff initials and date are required.")
                return

            # 3) Add the record via availability_manager
            self.availability_manager.add_availability(initials, date_str, reason)
            self.populate_listbox()
            popup.destroy()

        ttk.Button(popup, text="Add", command=add_avail_action).pack(pady=5)

    def add_holiday_popup(self):
        popup = tk.Toplevel(self.parent_frame)
        popup.title("Add Holiday")

        tk.Label(popup, text="Holiday Date (YYYY-MM-DD):").pack()
        date_entry = tk.Entry(popup)
        date_entry.pack()

        tk.Label(popup, text="Reason (optional):").pack()
        reason_entry = tk.Entry(popup)
        reason_entry.insert(0, "Holiday")
        reason_entry.pack()

        def add_holiday_action():
            date_str = date_entry.get().strip()
            reason = reason_entry.get().strip()
            if not date_str:
                messagebox.showerror("Validation Error", "Holiday date is required.")
                return

            # Build a record with is_holiday = True
            record = {
                "initials": "ALL",  # or "HOLIDAY" to indicate no staff needed
                "date": date_str,
                "reason": reason,
                "is_holiday": True
            }
            # store it
            self.availability_manager.add_record(record)

            # Refresh list
            self.populate_listbox()
            popup.destroy()

        ttk.Button(popup, text="Add Holiday", command=add_holiday_action).pack(pady=5)

    def remove_selected_record(self):
        selection = self.avail_listbox.curselection()
        if not selection:
            messagebox.showerror("No Selection", "Please select an availability record to remove.")
            return
        selected_line = self.avail_listbox.get(selection[0])
        parts = selected_line.split(" | ")
        if len(parts) < 2:
            return
        initials = parts[0].strip()
        date_str = parts[1].strip()

        if messagebox.askyesno("Confirm Removal", f"Remove availability for {initials}, {date_str}?"):
            success = self.availability_manager.remove_availability(initials, date_str)
            if success:
                self.populate_listbox()
            else:
                messagebox.showerror("Removal Error", "Could not remove availability.")
