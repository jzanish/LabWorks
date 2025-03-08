# availability_management/availability_gui.py

import calendar
from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QCalendarWidget
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

# If you have a multi-date approach for normal PTO:
from .multi_date_calendar import MultiDateAvailabilityDialog


# 1) Here's the little helper function:
def short_day_label(year, month, day_num):
    """
    Return a string like:  "13 (M)"  or  "13\nM"
    for the given year/month/day_num.
    """
    d_obj = date(year, month, day_num)

    # Minimal abbreviations of weekdays: M, T, W, Th, F, Sa, Su
    # Python's weekday(): Monday=0..Sunday=6
    short_names = ["M", "T", "W", "Th", "F", "Sa", "Su"]
    w = d_obj.weekday()  # 0..6

    # (A) Either multiline:
    return f"{short_names[w]}\n{day_num}"
    # (B) Or side by side:
    # return f"{day_num} ({short_names[w]})"


class AddHolidayDialog(QDialog):
    """
    A QDialog that displays a QCalendarWidget to pick exactly one date for a Holiday.
    """

    def __init__(self, parent, availability_manager):
        super().__init__(parent)
        self.setWindowTitle("Select Holiday Date")
        self.availability_manager = availability_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # A QCalendarWidget for single-date selection
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)

        # By default, highlight “today” or do nothing special

        # A small form layout for the reason
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        self.reason_edit = QLineEdit("Holiday")
        form_layout.addRow("Reason (optional):", self.reason_edit)

        # OK/Cancel
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # Optionally resize bigger:
        self.resize(400, 400)

    def _on_ok(self):
        # Convert QDate to Python date
        qdate = self.calendar.selectedDate()
        year = qdate.year()
        month = qdate.month()
        day = qdate.day()
        pydate = date(year, month, day)

        # Build the record
        record = {
            "initials": "ALL",  # or "HOLIDAY" if you prefer
            "date": pydate.isoformat(),  # "YYYY-MM-DD" string
            "reason": self.reason_edit.text().strip(),
            "is_holiday": True
        }
        self.availability_manager.add_record(record)
        self.accept()


class AvailabilityTab(QWidget):
    """
    A PySide6 version of your old Tk-based AvailabilityTab,
    now with a month-based table, plus remove & holiday.
    """

    def __init__(self, parent, availability_manager, staff_manager):
        super().__init__(parent)
        self.availability_manager = availability_manager
        self.staff_manager = staff_manager

        self._current_staff_inits = []
        self._current_day_strs = []

        self._build_ui()
        self._refresh_table()  # fill table by default

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # -- Top controls (month/year combos, etc.) --
        top_controls = QHBoxLayout()
        layout.addLayout(top_controls)

        self.month_combo = QComboBox()
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        for i, mname in enumerate(month_names, start=1):
            self.month_combo.addItem(mname, i)
        self.month_combo.setCurrentIndex(0)  # e.g. January
        top_controls.addWidget(self.month_combo)

        self.year_combo = QComboBox()
        for yr in range(2024, 2031):
            self.year_combo.addItem(str(yr), yr)
        self.year_combo.setCurrentText("2025")  # default
        top_controls.addWidget(self.year_combo)

        # Connect signals so we auto-refresh
        self.month_combo.currentIndexChanged.connect(self._refresh_table)
        self.year_combo.currentIndexChanged.connect(self._refresh_table)
        top_controls.addStretch(1)

        # The QTableWidget that displays staff vs days
        self.table = QTableWidget()
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        layout.addWidget(self.table)

        # Buttons row
        btn_row = QHBoxLayout()
        layout.addLayout(btn_row)

        multi_btn = QPushButton("Add Availability")
        multi_btn.clicked.connect(self._on_add_availability_calendar)
        btn_row.addWidget(multi_btn)

        holiday_btn = QPushButton("Add Holiday")
        holiday_btn.clicked.connect(self._on_add_holiday)
        btn_row.addWidget(holiday_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._on_remove_selected)
        btn_row.addWidget(remove_btn)

        btn_row.addStretch(1)

        self.setLayout(layout)

    def _refresh_table(self):
        month_idx = self.month_combo.currentIndex()
        month = self.month_combo.itemData(month_idx)
        year_idx = self.year_combo.currentIndex()
        year = self.year_combo.itemData(year_idx)
        if not (month and year):
            QMessageBox.warning(self, "Invalid Selection", "No valid month/year selected.")
            return

        num_days = calendar.monthrange(year, month)[1]

        # Gather staff
        staff_objs = sorted(self.staff_manager.list_staff(), key=lambda s: s.initials)
        row_count = len(staff_objs)
        col_count = num_days

        self.table.clear()
        self.table.setRowCount(row_count)
        self.table.setColumnCount(col_count)

        # Build day labels but with short_day_label() instead of just str(day_num)
        day_labels = []
        self._current_day_strs = []

        for c in range(num_days):
            day_num = c + 1
            # Use the helper to produce e.g. "13 (M)" or "13\nM"
            label_text = short_day_label(year, month, day_num)
            day_labels.append(label_text)

            from datetime import date as dt_date
            actual_date = dt_date(year, month, day_num)
            self._current_day_strs.append(actual_date.strftime("%Y-%m-%d"))

        self.table.setHorizontalHeaderLabels(day_labels)

        # staff_inits
        staff_inits = [s.initials for s in staff_objs]
        self._current_staff_inits = staff_inits
        self.table.setVerticalHeaderLabels(staff_inits)

        # Make columns stretch
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Build availability map
        avails = self.availability_manager.list_availability()
        availability_map = {}
        holiday_days = set()

        for rec in avails:
            d_str = rec["date"]
            reason = rec.get("reason", "")
            init = rec["initials"]
            if not rec.get("is_holiday", False):
                availability_map[(init, d_str)] = reason
            else:
                holiday_days.add(d_str)

        # Fill each cell
        for r, stf in enumerate(staff_objs):
            init = stf.initials
            for c in range(num_days):
                d_str = self._current_day_strs[c]
                if d_str in holiday_days:
                    color = QColor("teal")
                    reason = "Holiday"
                else:
                    reason = availability_map.get((init, d_str), "")
                    if reason == "PTO":
                        color = QColor("green")
                    elif reason in ("0.5 FTE", "0.8 FTE"):
                        color = QColor("blue")
                    elif reason == "SSL":
                        color = QColor("red")
                    elif reason:
                        color = QColor("yellow")
                    else:
                        color = None

                item = QTableWidgetItem("")
                if color:
                    item.setBackground(color)
                if reason:
                    item.setToolTip(reason)

                self.table.setItem(r, c, item)

        self.table.resizeRowsToContents()

    def _on_add_availability_calendar(self):
        dialog = MultiDateAvailabilityDialog(
            parent=self,
            availability_manager=self.availability_manager,
            staff_manager=self.staff_manager
        )
        if dialog.exec() == QDialog.Accepted:
            self._refresh_table()

    def _on_add_holiday(self):
        dialog = AddHolidayDialog(self, self.availability_manager)
        if dialog.exec() == QDialog.Accepted:
            self._refresh_table()

    def _on_remove_selected(self):
        items = self.table.selectedIndexes()
        if not items:
            QMessageBox.warning(self, "No Selection", "Please select a cell to remove.")
            return

        idx = items[0]
        row = idx.row()
        col = idx.column()
        if row < 0 or row >= len(self._current_staff_inits):
            return
        staff_init = self._current_staff_inits[row]
        if col < 0 or col >= len(self._current_day_strs):
            return
        date_str = self._current_day_strs[col]

        resp = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove availability for {staff_init}, {date_str}?"
        )
        if resp != QMessageBox.Yes:
            return

        success = self.availability_manager.remove_availability(staff_init, date_str)
        if success:
            self._refresh_table()
        else:
            QMessageBox.critical(self, "Removal Error",
                                 f"Could not remove availability for {staff_init}, {date_str}.")
