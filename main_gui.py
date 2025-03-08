# main_gui_qt.py

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QLabel, QStatusBar, QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt

# ---- import your managers ----
from staff_management.manager import StaffManager
from shift_management.manager import ShiftManager
from availability_management.manager import AvailabilityManager
from scheduler.scheduler import ORToolsScheduler
from schedule_review.manager import ReviewManager

# ---- import your PyQt-based tabs (the newly converted classes) ----
from staff_management.staff_gui import StaffTab
from shift_management.shift_gui import ShiftTab
from availability_management.availability_gui import AvailabilityTab
from scheduler.scheduler_gui import SchedulerTab
from schedule_review.schedule_review_gui import ScheduleReviewTab


class CytologySchedulerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CYTOLOGY SCHEDULER - PyQt Edition")
        self.resize(1700, 900)
  
        # Create managers
        try:
            self.shift_manager = ShiftManager()
            self.staff_manager = StaffManager(shift_manager=self.shift_manager)
            self.availability_manager = AvailabilityManager()
            self.ortools_scheduler = ORToolsScheduler(
                self.staff_manager,
                self.shift_manager,
                self.availability_manager
            )
            self.review_manager = ReviewManager(schedules_dir="data/schedules")
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to init managers: {e}")
            return

        # Main widget to hold everything
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout for the central widget
        main_layout = QVBoxLayout(central_widget)

        # Create QTabWidget (like a Notebook)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget, stretch=1)

        # Staff Tab
        self.staff_tab = StaffTab(self.tab_widget, self.staff_manager, self.shift_manager)
        self.tab_widget.addTab(self.staff_tab, "Staff Management")

        # Shift Tab
        self.shift_tab = ShiftTab(self.tab_widget, self.shift_manager)
        self.tab_widget.addTab(self.shift_tab, "Shift Management")

        # Availability Tab
        self.availability_tab = AvailabilityTab(
            self.tab_widget,
            self.availability_manager,
            self.staff_manager
        )
        self.tab_widget.addTab(self.availability_tab, "Availability")

        # Scheduler Tab
        self.scheduler_tab = SchedulerTab(
            self.tab_widget,
            self.ortools_scheduler,
            self.staff_manager,
            self.shift_manager,
            review_manager=self.review_manager,
            availability_manager=self.availability_manager
        )
        self.tab_widget.addTab(self.scheduler_tab, "Scheduler")

        # Schedule Review Tab
        self.review_tab = ScheduleReviewTab(
            self.tab_widget,
            self.review_manager,
            self.staff_manager
        )
        self.tab_widget.addTab(self.review_tab, "Schedule Review")

        # A horizontal layout for global controls
        self._create_global_controls(main_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Welcome!")
        self.setStatusBar(self.status_bar)

    def _create_global_controls(self, parent_layout):
        control_layout = QHBoxLayout()
        parent_layout.addLayout(control_layout)

        refresh_button = QPushButton("Refresh All Tabs")
        refresh_button.clicked.connect(self._refresh_all_tabs)
        control_layout.addWidget(refresh_button)

        save_button = QPushButton("Save All Data")
        save_button.clicked.connect(self._save_all_data)
        control_layout.addWidget(save_button)

        # Add some stretch so these buttons stay on the left
        control_layout.addStretch(1)

    def _refresh_all_tabs(self):
        try:
            # If your PyQt-based tabs have a refresh method, call them here:
            #   self.staff_tab.refresh()
            #   self.shift_tab.refresh()
            #   ...
            # For now, just a debug message:
            self.status_bar.showMessage("All tabs refreshed!")
            print("DEBUG: All tabs refreshed successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Refresh Error", f"Could not refresh: {e}")
            self.status_bar.showMessage(str(e))
            print(f"ERROR: Could not refresh tabs - {e}")

    def _save_all_data(self):
        try:
            self.staff_manager.save_data()
            self.shift_manager.save_data()
            self.availability_manager.save_data()

            QMessageBox.information(self, "Data Saved", "All data saved successfully!")
            print("DEBUG: All data saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save data: {e}")
            print(f"ERROR: Could not save data - {e}")


def main():
    app = QApplication(sys.argv)
    window = CytologySchedulerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
