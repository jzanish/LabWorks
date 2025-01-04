# availability_management/availability_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from datetime import datetime, timedelta
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
        popup.title("Add Availability (Multiple Dates / Range)")

        # 1) Get the list of staff from staff_manager
        staff_list = self.staff_manager.list_staff()
        valid_initials = [s.initials for s in staff_list]

        tk.Label(popup, text="Staff Initials:").pack()
        staff_initials_combo = ttk.Combobox(
            popup,
            values=sorted(valid_initials),  # alphabetically sorted
            state="readonly"
        )
        if valid_initials:
            staff_initials_combo.current(0)
        staff_initials_combo.pack(pady=2)

        # Multi-line text for dates
        label = tk.Label(
            popup,
            text=(
                "Note:\n"
                "• Date Format: (YYYY-MM-DD):\n"
                "• Single Date: 2025-03-10\n"
                "• Multiple (comma/newline): 2025-03-10, 2025-03-12\n"
                "• Range (dash): 2025-03-10 - 2025-03-13"
            ),
            anchor="w",
            justify="left"
        )
        label.pack(fill="x", padx=5, pady=5)

        dates_text = tk.Text(popup, width=30, height=4)
        dates_text.pack(pady=2)

        tk.Label(popup, text="Reason:").pack()
        reason_entry = tk.Entry(popup)
        reason_entry.insert(0, "PTO")
        reason_entry.pack(pady=2)

        def add_avail_action():
            initials = staff_initials_combo.get().strip()
            raw_dates = dates_text.get("1.0", tk.END).strip()
            reason = reason_entry.get().strip()

            if not initials:
                messagebox.showerror("Validation Error", "Please select a Staff Initials.")
                return

            if not raw_dates:
                messagebox.showerror("Validation Error", "Please enter at least one date.")
                return

            # 1) Split lines; handle multiple lines/commas
            lines = []
            for line in raw_dates.split("\n"):
                line = line.strip()
                if line:
                    lines.extend([x.strip() for x in line.split(",") if x.strip()])

            # 2) We'll accumulate final date strings in all_dates
            all_dates = []
            for entry in lines:
                # Normalize fancy dashes
                entry = entry.replace("–", "-").replace("—", "-")

                # Check for space-hyphen-space to parse as range
                if " - " in entry:
                    parts = [p.strip() for p in entry.split(" - ")]
                    if len(parts) == 2:
                        start_str, end_str = parts
                        try:
                            start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
                            end_dt = datetime.strptime(end_str, "%Y-%m-%d").date()
                            if end_dt < start_dt:
                                raise ValueError("End date before start date in range.")
                            cursor = start_dt
                            while cursor <= end_dt:
                                all_dates.append(cursor.strftime("%Y-%m-%d"))
                                cursor += timedelta(days=1)
                        except ValueError as ve:
                            messagebox.showerror(
                                "Invalid Range",
                                f"Could not parse date range '{entry}': {ve}"
                            )
                    else:
                        messagebox.showerror(
                            "Invalid Range",
                            f"Date range format should be 'YYYY-MM-DD - YYYY-MM-DD' not '{entry}'."
                        )
                else:
                    # No " - " substring => treat as a single date (or multiple single dates)
                    try:
                        dt = datetime.strptime(entry, "%Y-%m-%d").date()
                        all_dates.append(dt.strftime("%Y-%m-%d"))
                    except ValueError:
                        messagebox.showerror(
                            "Invalid Date",
                            f"Could not parse date '{entry}'. Must be YYYY-MM-DD."
                        )

            if not all_dates:
                return  # user typed invalid stuff or canceled

            # 3) Add them all
            count_added = 0
            for date_str in all_dates:
                self.availability_manager.add_availability(initials, date_str, reason)
                count_added += 1

            self.populate_listbox()
            messagebox.showinfo("Availability Added",
                                f"Added {count_added} availability record(s).")
            popup.destroy()

        ttk.Button(popup, text="Add Availability", command=add_avail_action).pack(pady=5)

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
                "initials": "ALL",  # or "HOLIDAY"
                "date": date_str,
                "reason": reason,
                "is_holiday": True
            }
            self.availability_manager.add_record(record)
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
