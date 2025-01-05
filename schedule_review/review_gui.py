# schedule_review/review_gui_qt.py

import json
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QDialog, QLabel,
    QDialogButtonBox, QComboBox, QFormLayout, QLineEdit, QCheckBox,
    QGridLayout
)
from PySide6.QtCore import Qt


class ScheduleReviewTab(QWidget):
    """
    A GUI tab that displays a list of committed schedules (from ReviewManager),
    allows selecting one, and then 'View/Edit' in a combobox grid style.
    """
    def __init__(self, parent, review_manager, staff_manager):
        """
        :param parent: The parent widget (e.g., QTabWidget).
        :param review_manager: An instance of ReviewManager.
        :param staff_manager: So we can get staff initials for the combos.
        """
        super().__init__(parent)
        self.review_manager = review_manager
        self.staff_manager = staff_manager

        self._build_ui()
        self._populate_schedule_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Main area: list of schedules
        self.history_box = QGroupBox("Saved Schedules")
        layout.addWidget(self.history_box)

        box_layout = QVBoxLayout(self.history_box)
        self.schedule_listwidget = QListWidget()
        box_layout.addWidget(self.schedule_listwidget)

        # Button row
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        view_btn = QPushButton("View/Edit Schedule")
        view_btn.clicked.connect(self._edit_schedule)
        btn_layout.addWidget(view_btn)

        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete_schedule)
        btn_layout.addWidget(del_btn)

        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self._populate_schedule_list)
        btn_layout.addWidget(refresh_btn)

        # Add stretch so buttons stay left
        btn_layout.addStretch(1)

    def _populate_schedule_list(self):
        """
        Re-list all schedules from review_manager in the list widget.
        """
        self.schedule_listwidget.clear()
        schedules = self.review_manager.list_schedules()
        for i, sched in enumerate(schedules):
            start_date = sched.get("start_date", "unknown")
            end_date = sched.get("end_date", "unknown")
            version = sched.get("version", "")
            line = f"{start_date} -> {end_date} (v:{version})"
            item = QListWidgetItem(line)
            self.schedule_listwidget.addItem(item)

    def _get_selected_index(self):
        row = self.schedule_listwidget.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a schedule from the list.")
            return None
        return row

    def _edit_schedule(self):
        idx = self._get_selected_index()
        if idx is None:
            return
        sched_data = self.review_manager.list_schedules()[idx]

        dialog = ScheduleEditDialog(
            self,
            schedule_data=sched_data,
            staff_manager=self.staff_manager,
            on_save=lambda updated: self._handle_schedule_save(idx, updated)
        )
        dialog.exec()

    def _handle_schedule_save(self, index, updated_data):
        """
        Called after the user clicks 'OK' in the ScheduleEditDialog.
        We update the schedule in memory, and optionally re-save to disk.
        """
        self.review_manager.update_schedule(index, updated_data)
        QMessageBox.information(self, "Saved", "Schedule updated in review history.")
        self._populate_schedule_list()

    def _delete_schedule(self):
        idx = self._get_selected_index()
        if idx is None:
            return
        resp = QMessageBox.question(self, "Confirm", "Delete this schedule from review?")
        if resp == QMessageBox.Yes:
            success = self.review_manager.delete_schedule(idx)
            if success:
                QMessageBox.information(self, "Deleted", "Schedule removed.")
                self._populate_schedule_list()


# ---------------------------------------------------------------------------
# The dialog for viewing/editing a single schedule using combos in a grid
# ---------------------------------------------------------------------------
class ScheduleEditDialog(QDialog):
    """
    A QDialog that shows day columns, shift rows, and each cell is a combobox
    for staff initials, pre-filled from schedule_data's assignments.
    """
    def __init__(self, parent, schedule_data, staff_manager, on_save=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Schedule (Combobox Grid)")
        self.schedule_data = schedule_data
        self.staff_manager = staff_manager
        self.on_save = on_save

        self.cell_widgets = {}  # (day, shift_name) -> QComboBox

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # parse days
        assignments = self.schedule_data.get("assignments", {})
        self.day_list = sorted(assignments.keys())

        # parse all shift names from the data itself
        shift_set = set()
        for day_str in self.day_list:
            for rec in assignments[day_str]:
                shift_set.add(rec["shift"])
        self.shift_list = sorted(shift_set)

        # gather staff initials
        staff_inits = sorted([s.initials for s in self.staff_manager.list_staff()])

        # We'll build a grid of combos
        from PySide6.QtWidgets import QGridLayout, QLabel, QComboBox, QDialogButtonBox
        grid = QGridLayout()
        layout.addLayout(grid)

        # row=0 => day headings
        corner_lbl = QLabel("Shift / Day")
        grid.addWidget(corner_lbl, 0, 0)

        for col_idx, day_str in enumerate(self.day_list, start=1):
            day_obj = datetime.strptime(day_str, "%Y-%m-%d")
            heading_text = day_obj.strftime("%a %d")
            lbl = QLabel(heading_text)
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, 0, col_idx)

        # For each shift, create a row
        for row_idx, shift_name in enumerate(self.shift_list, start=1):
            shift_lbl = QLabel(shift_name)
            grid.addWidget(shift_lbl, row_idx, 0)

            for col_idx, day_str in enumerate(self.day_list, start=1):
                # find who is assigned
                assigned_staff = "None"
                for rec in assignments[day_str]:
                    if rec["shift"] == shift_name:
                        assigned_staff = rec["assigned_to"]
                        break

                combo = QComboBox()
                combo.addItem("None")
                for s_init in staff_inits:
                    combo.addItem(s_init)
                if assigned_staff and assigned_staff != "Unassigned":
                    # set current
                    index = combo.findText(assigned_staff)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                    else:
                        # staff not in combo
                        combo.addItem(assigned_staff)
                        combo.setCurrentText(assigned_staff)

                grid.addWidget(combo, row_idx, col_idx)
                self.cell_widgets[(day_str, shift_name)] = combo

        # OK/Cancel
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.setLayout(layout)

        # Expand columns so combos look good
        col_count = len(self.day_list) + 1
        for c in range(col_count):
            grid.setColumnStretch(c, 1)

    def _on_ok(self):
        """
        Build an updated schedule_data from the combos, then call on_save(updated_data).
        """
        updated_assignments = {}
        old_assignments = self.schedule_data.get("assignments", {})

        for day_str in self.day_list:
            updated_assignments[day_str] = []

        # shift_list
        for day_str in self.day_list:
            for shift_name in self.shift_list:
                combo = self.cell_widgets.get((day_str, shift_name))
                if combo:
                    assigned = combo.currentText()
                    if assigned == "None":
                        assigned = "Unassigned"
                    # we might also keep 'role', 'is_flexible', etc. if needed
                    updated_assignments[day_str].append({
                        "shift": shift_name,
                        "assigned_to": assigned
                    })

        new_data = dict(self.schedule_data)
        new_data["assignments"] = updated_assignments

        if self.on_save:
            self.on_save(new_data)
        self.accept()
