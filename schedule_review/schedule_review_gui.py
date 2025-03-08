# schedule_review_gui.py

import os
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QMessageBox, QDialog
)
from PySide6.QtCore import Qt

# Adjust your imports to match your folder structure
from .analytics_gui import AnalyticsWidget
from .manual_edit_widget import ManualEditWidget
from .analytics import ScheduleAnalytics
from .select_schedule_dialog import SelectScheduleDialog


class ShiftFilterDialog(QDialog):
    """
    A dialog with checkboxes for each shift name.
    `default_selected` = set of shifts to be checked by default.
    If `default_selected` is None => interpret as "check them all".
    """
    def __init__(self, parent, shift_list, default_selected=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Shifts")
        self.shift_list = sorted(shift_list)

        if default_selected is None:
            # If None, interpret as "all shifts checked."
            self.default_selected = set(self.shift_list)
        else:
            self.default_selected = set(default_selected)

        self.selected_shifts = set()
        self._build_ui()

    def _build_ui(self):
        from PySide6.QtWidgets import QVBoxLayout, QDialogButtonBox, QCheckBox

        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        self.checkboxes = []
        for shift_name in self.shift_list:
            cb = QCheckBox(shift_name, self)
            # Check if shift_name is in the default set
            cb.setChecked(shift_name in self.default_selected)
            self.checkboxes.append(cb)
            main_layout.addWidget(cb)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

    def _on_ok(self):
        # Gather all selected shifts
        for cb in self.checkboxes:
            if cb.isChecked():
                self.selected_shifts.add(cb.text())
        self.accept()

    def get_selected_shifts(self):
        return self.selected_shifts


class ScheduleReviewTab(QWidget):
    """
    A tab that shows:
      - A button to pick a saved schedule
      - Buttons to filter included shifts for two charts:
         1) Weekly Effort chart
         2) SHIFT Count chart
      - Manual edit area for SHIFT-based editing
      - On the right: an AnalyticsWidget that can show both
        (weekly effort) and (shift counts) side by side.
    """

    # Default shift names for SHIFT Count chart
    SHIFT_COUNT_DEFAULTS = {"Cyto FNA", "Cyto EUS", "Cyto MCY", "Cyto UTD"}

    def __init__(self, parent, review_manager, staff_manager, availability_manager=None):
        super().__init__(parent)
        self.review_manager = review_manager
        self.staff_manager = staff_manager
        self.availability_manager = availability_manager

        self.current_sched_data = None  # store the currently loaded schedule
        self.included_shifts = None     # used for weekly effort (None => all)
        self.included_shifts_for_counts = None  # used for shift counts

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # ---- Top Buttons row ----
        top_btn_row = QHBoxLayout()
        layout.addLayout(top_btn_row)

        self.select_btn = QPushButton("Select Saved Schedule")
        self.select_btn.clicked.connect(self._on_select_schedule)
        top_btn_row.addWidget(self.select_btn)

        # Filter for weekly effort
        self.filter_btn = QPushButton("Filter Shifts (Weekly Effort)")
        self.filter_btn.clicked.connect(self._on_filter_shifts)
        top_btn_row.addWidget(self.filter_btn)

        # SHIFT Count button
        self.shift_count_btn = QPushButton("Show SHIFT Counts")
        self.shift_count_btn.clicked.connect(self._on_show_shift_counts)
        top_btn_row.addWidget(self.shift_count_btn)

        top_btn_row.addStretch(1)

        # ---- Main content row: ManualEditWidget + AnalyticsWidget
        content_row = QHBoxLayout()
        layout.addLayout(content_row, stretch=1)

        # The SHIFT-based schedule editor
        self.manual_edit = ManualEditWidget(
            self,
            review_manager=self.review_manager,
            staff_manager=self.staff_manager
        )
        content_row.addWidget(self.manual_edit, stretch=2)

        # The analytics widget that can show both
        self.analytics_view = AnalyticsWidget(self)
        content_row.addWidget(self.analytics_view, stretch=1)

    # ------------------------------------------------------------
    #  LOAD SCHEDULE: show Weekly Effort *and* SHIFT counts by default
    # ------------------------------------------------------------
    def _on_select_schedule(self):
        dlg = SelectScheduleDialog(self, self.review_manager)
        if dlg.exec() == QDialog.Accepted:
            chosen_info = dlg.get_chosen_schedule_info()
            if not chosen_info:
                return

            sched_data = self.review_manager.load_schedule(chosen_info["filename"])
            if not sched_data:
                QMessageBox.critical(self, "Error", f"Failed to load schedule {chosen_info['filename']}")
                return

            self.current_sched_data = sched_data
            # Load into ManualEditWidget
            self.manual_edit.load_schedule(sched_data)

            # Gather EBUS Fridays if present
            if hasattr(self.review_manager, "get_ebus_fridays"):
                ebus_fr = set(self.review_manager.get_ebus_fridays())
            else:
                ebus_fr = set()

            analyzer = ScheduleAnalytics(ebus_fridays=ebus_fr)

            # 1) Weekly Effort with self.included_shifts => None => "all"
            weekly_data = analyzer.calc_weekly_effort(
                sched_data,
                included_shifts=self.included_shifts
            )
            self.analytics_view.display_weekly_effort_bar(weekly_data)

            # 2) SHIFT Count with SHIFT_COUNT_DEFAULTS => so it won't be blank
            shift_counts = analyzer.calc_shift_counts(
                sched_data,
                included_shifts=self.SHIFT_COUNT_DEFAULTS
            )
            self.included_shifts_for_counts = self.SHIFT_COUNT_DEFAULTS
            self.analytics_view.display_shift_count_bar(shift_counts)

    # ------------------------------------------------------------
    #  FILTER SHIFT(s) FOR THE WEEKLY EFFORT CHART
    # ------------------------------------------------------------
    def _on_filter_shifts(self):
        if not self.current_sched_data:
            QMessageBox.warning(self, "No Schedule", "Load a schedule first.")
            return

        shift_list = self._gather_shift_names_from_current()
        if not shift_list:
            QMessageBox.information(self, "No Shifts", "No shifts in this schedule.")
            return

        # Default = None => all checked
        dlg = ShiftFilterDialog(self, shift_list, default_selected=None)
        if dlg.exec() == QDialog.Accepted:
            self.included_shifts = dlg.get_selected_shifts()

            # Re-run the weekly chart
            if hasattr(self.review_manager, "get_ebus_fridays"):
                ebus_fr = set(self.review_manager.get_ebus_fridays())
            else:
                ebus_fr = set()

            analyzer = ScheduleAnalytics(ebus_fridays=ebus_fr)
            weekly_data = analyzer.calc_weekly_effort(
                self.current_sched_data,
                included_shifts=self.included_shifts
            )
            self.analytics_view.display_weekly_effort_bar(weekly_data)

    # ------------------------------------------------------------
    #  SHIFT COUNT CHART (with default SHIFT_COUNT_DEFAULTS)
    # ------------------------------------------------------------
    def _on_show_shift_counts(self):
        if not self.current_sched_data:
            QMessageBox.warning(self, "No Schedule", "Please load a schedule first.")
            return

        shift_list = self._gather_shift_names_from_current()
        if not shift_list:
            QMessageBox.information(self, "No Shifts", "No shifts in this schedule.")
            return

        # Default = SHIFT_COUNT_DEFAULTS => we pass that as default_selected
        dlg = ShiftFilterDialog(self, shift_list, default_selected=self.SHIFT_COUNT_DEFAULTS)
        if dlg.exec() == QDialog.Accepted:
            self.included_shifts_for_counts = dlg.get_selected_shifts()

            analyzer = ScheduleAnalytics()
            shift_counts = analyzer.calc_shift_counts(
                self.current_sched_data,
                included_shifts=self.included_shifts_for_counts
            )
            self.analytics_view.display_shift_count_bar(shift_counts)

    # ------------------------------------------------------------
    #  Utility: gather shift names from the loaded schedule
    # ------------------------------------------------------------
    def _gather_shift_names_from_current(self):
        if not self.current_sched_data:
            return []

        all_shifts = set()
        for day_str, rec_list in self.current_sched_data.get("assignments", {}).items():
            for rec in rec_list:
                sh_nm = rec.get("shift", "")
                if sh_nm:
                    all_shifts.add(sh_nm)
        return sorted(all_shifts)
