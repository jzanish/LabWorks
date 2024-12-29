# main_gui.py

import tkinter as tk
from tkinter import ttk, messagebox

from staff_management.staff_gui import StaffTab
from staff_management.manager import StaffManager

from shift_management.shift_gui import ShiftTab
from shift_management.manager import ShiftManager

from availability_management.availability_gui import AvailabilityTab
from availability_management.manager import AvailabilityManager

from scheduler.scheduler import ORToolsScheduler
from scheduler.scheduler_gui import SchedulerTab

# NEW IMPORTS for constraints
from constraint_editor.manager import ConstraintsManager
from constraint_editor.constraint_gui import ConstraintsEditorTab


class CytologyScheduler:
    def __init__(self, root):
        self.root = root
        self.root.title("CYTOLOGY SCHEDULER")
        self.root.geometry("1000x900")

        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Welcome!")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

        try:
            self.shift_manager = ShiftManager()
            self.staff_manager = StaffManager(shift_manager=self.shift_manager)
            self.availability_manager = AvailabilityManager()
            self.ortools_scheduler = ORToolsScheduler(self.staff_manager, self.shift_manager, self.availability_manager)

            # Initialize ConstraintsManager after we have staff/shift managers
            self.constraints_manager = ConstraintsManager(self.staff_manager, self.shift_manager)

        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to init managers: {e}")
            return

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")

        # Staff Tab
        self.staff_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.staff_tab_frame, text="Staff Management")
        self.staff_tab = StaffTab(self.staff_tab_frame, self.staff_manager, self.shift_manager)

        # Shift Tab
        self.shift_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.shift_tab_frame, text="Shift Management")
        self.shift_tab = ShiftTab(self.shift_tab_frame, self.shift_manager)

        # Constraints Tab
        self.constraints_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.constraints_tab_frame, text="Constraints")
        self.constraints_tab = ConstraintsEditorTab(
            self.constraints_tab_frame,
            self.constraints_manager,
            self.staff_manager,
            self.shift_manager,
        )

        # Availability Tab
        self.availability_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.availability_tab_frame, text="Availability")
        self.availability_tab = AvailabilityTab(
            parent_frame=self.availability_tab_frame,
            availability_manager=self.availability_manager,
            staff_manager=self.staff_manager
        )

        # Scheduler Tab
        self.scheduler_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.scheduler_tab_frame, text="Scheduler")
        self.scheduler_tab = SchedulerTab(
            self.scheduler_tab_frame,
            self.ortools_scheduler,
            self.staff_manager
        )


        self._create_global_controls()

    def _create_global_controls(self):
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=5)

        refresh_button = ttk.Button(control_frame, text="Refresh All Tabs", command=self._refresh_all_tabs)
        refresh_button.pack(side="left", padx=5, pady=5)

        save_button = ttk.Button(control_frame, text="Save All Data", command=self._save_all_data)
        save_button.pack(side="left", padx=5, pady=5)

        print("DEBUG: Global control buttons created.")

    def _refresh_all_tabs(self):
        try:
            self.staff_tab.populate_listbox()
            self.shift_tab._refresh_shift_list()
            self.availability_tab.populate_listbox()
            # If your constraints tab has a refresh method, call it too:
            self.constraints_tab._populate_constraint_list()

            self.status_var.set("All tabs refreshed!")
            print("DEBUG: All tabs refreshed successfully.")
        except Exception as e:
            messagebox.showerror("Refresh Error", f"Could not refresh: {e}")
            self.status_var.set(str(e))
            print(f"ERROR: Could not refresh tabs - {e}")

    def _save_all_data(self):
        try:
            self.staff_manager.save_data()
            self.shift_manager.save_data()
            self.availability_manager.save_data()
            # Also save constraints:
            self.constraints_manager.save_data()

            messagebox.showinfo("Data Saved", "All data saved successfully!")
            print("DEBUG: All data saved successfully.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save data: {e}")
            print(f"ERROR: Could not save data - {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = CytologyScheduler(root)
    root.mainloop()
