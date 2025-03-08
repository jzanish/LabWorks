# manual_edit_widget.py

import json
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt

class ManualEditWidget(QWidget):
    """
    Lets you view/edit SHIFT-based schedule data in a QTableWidget.
    On 'Save' you push changes back to the schedule_data in memory (or disk).
    """
    def __init__(self, parent, review_manager, staff_manager):
        super().__init__(parent)
        self.review_manager = review_manager
        self.staff_manager = staff_manager

        self.current_schedule_data = None  # Will hold the loaded schedule
        self._day_list = []
        self._shift_names = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.info_label = QLabel("No schedule loaded.")
        layout.addWidget(self.info_label)

        self.table = QTableWidget()
        # Optionally, let the user select and edit cells
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        layout.addLayout(btn_row)

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        btn_row.addStretch(1)

    def load_schedule(self, schedule_data: dict):
        """
        Load the schedule_data (dict) into the table for editing.
        Expects schedule_data to have an 'assignments' dict: { day_str: [ {shift=..., assigned_to=..., role=...}, ... ], ... }
        """
        if not schedule_data or "assignments" not in schedule_data:
            self.info_label.setText("No schedule loaded (missing 'assignments').")
            self.current_schedule_data = None
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        self.current_schedule_data = schedule_data
        self.info_label.setText(
            f"Loaded schedule: {schedule_data.get('start_date', '?')} -> {schedule_data.get('end_date', '?')}"
        )

        # 1) figure out day_list
        self._day_list = sorted(schedule_data["assignments"].keys(),
                                key=lambda d: datetime.strptime(d, "%Y-%m-%d"))

        # 2) build shift_map => shift_name -> {day_str: staff_init, role=...}
        #    We'll store each day's assignment as (staff_init, role).
        shift_map = {}
        for day_str in self._day_list:
            rec_list = schedule_data["assignments"].get(day_str, [])
            for rec in rec_list:
                sh_name = rec["shift"]
                stf_init = rec["assigned_to"]
                role_val = rec.get("role", "Unknown")
                if sh_name not in shift_map:
                    shift_map[sh_name] = {}
                shift_map[sh_name][day_str] = (stf_init, role_val)

        # 3) If you have a known shift_order you can use it. Otherwise just sort by name
        self._shift_names = sorted(shift_map.keys())

        row_count = len(self._shift_names)
        col_count = len(self._day_list)

        self.table.clear()
        self.table.setRowCount(row_count)
        self.table.setColumnCount(col_count)

        # Horizontal headers => e.g. "Mon 2/10"
        date_headers = []
        for d_str in self._day_list:
            dt_obj = datetime.strptime(d_str, "%Y-%m-%d")
            date_headers.append(dt_obj.strftime("%a %m/%d"))
        self.table.setHorizontalHeaderLabels(date_headers)

        # Vertical headers => shift names
        self.table.setVerticalHeaderLabels(self._shift_names)

        # Fill table
        for r, sh_name in enumerate(self._shift_names):
            day_dict = shift_map[sh_name]  # => { day_str: (staff_init, role_val) }
            for c, d_str in enumerate(self._day_list):
                if d_str in day_dict:
                    stf_init, role_val = day_dict[d_str]
                else:
                    stf_init, role_val = ("Unassigned", "Unknown")

                # We'll store just the staff init text in the cell for editing
                item_text = stf_init
                cell_item = QTableWidgetItem(item_text)
                cell_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                # Optionally store the 'role' as data
                cell_item.setData(Qt.UserRole, role_val)

                self.table.setItem(r, c, cell_item)

    def _on_save(self):
        """
        Gather the table data back into self.current_schedule_data
        and optionally push changes to review_manager or disk.
        """
        if not self.current_schedule_data:
            QMessageBox.warning(self, "No Schedule", "No schedule loaded to save.")
            return

        assignments = {}
        for c, d_str in enumerate(self._day_list):
            assignments[d_str] = []

        # Rebuild from table
        for r, sh_name in enumerate(self._shift_names):
            for c, d_str in enumerate(self._day_list):
                item = self.table.item(r, c)
                if item:
                    stf_init = item.text()
                    role_val = item.data(Qt.UserRole)
                    if not role_val:
                        role_val = "Unknown"
                else:
                    stf_init = "Unassigned"
                    role_val = "Unknown"

                assignments[d_str].append({
                    "shift": sh_name,
                    "assigned_to": stf_init,
                    "role": role_val
                })

        self.current_schedule_data["assignments"] = assignments

        # Debug/log
        print("DEBUG: Updated schedule_data in memory:")
        print(json.dumps(self.current_schedule_data, indent=2))

        # Optionally call something like:
        # index = ???  # you'd need to know which schedule index or filename
        # self.review_manager.update_schedule(index, self.current_schedule_data)
        # or re-save using the old filename if your schedule_data had 'version' or 'filename'
        # For now, just show a message:
        QMessageBox.information(self, "Saved", "Schedule changes updated in memory (see console).")
