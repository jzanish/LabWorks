# availability_management/availability_gui_qt.py

import calendar
from datetime import date

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
            "initials": "ALL",       # or "HOLIDAY" if you prefer
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

        # We'll store staff initials & day strings in instance vars
        # so the remove function can easily map (row, col).
        self._current_staff_inits = []
        self._current_day_strs = []

        self._build_ui()
        self._refresh_table()  # fill table by default

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # -- Top controls (month/year combos, plus "Show" button) --
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

        self.month_combo.currentIndexChanged.connect(self._refresh_table)
        self.year_combo.currentIndexChanged.connect(self._refresh_table)

        top_controls.addStretch(1)

        # Table: staff vs days
        self.table = QTableWidget()
        # let user select single cells
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        layout.addWidget(self.table)

        # -- Buttons row: Add Avail (Calendar), Holiday, Remove, etc. --
        btn_row = QHBoxLayout()
        layout.addLayout(btn_row)

        # 1) Add Availability (Calendar) => normal PTO or partial FTE
        multi_btn = QPushButton("Add Availability")
        multi_btn.clicked.connect(self._on_add_availability_calendar)
        btn_row.addWidget(multi_btn)

        # 2) Add Holiday => uses single-date QCalendar
        holiday_btn = QPushButton("Add Holiday")
        holiday_btn.clicked.connect(self._on_add_holiday)
        btn_row.addWidget(holiday_btn)

        # 3) Remove Selected
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._on_remove_selected)
        btn_row.addWidget(remove_btn)

        btn_row.addStretch(1)

    def _refresh_table(self):
        # 1) Determine chosen month/year
        month_idx = self.month_combo.currentIndex()
        month = self.month_combo.itemData(month_idx)
        year_idx = self.year_combo.currentIndex()
        year = self.year_combo.itemData(year_idx)
        if not (month and year):
            QMessageBox.warning(self, "Invalid Selection", "No valid month/year selected.")
            return

        # 2) Number of days in that month
        num_days = calendar.monthrange(year, month)[1]

        # 3) Gather staff
        staff_objs = sorted(self.staff_manager.list_staff(), key=lambda s: s.initials)
        row_count = len(staff_objs)
        col_count = num_days

        self.table.clear()
        self.table.setRowCount(row_count)
        self.table.setColumnCount(col_count)

        # Build day labels + store day_str for each column
        day_labels = []
        self._current_day_strs = []
        from datetime import date as dt_date
        for c in range(num_days):
            day_num = c + 1
            day_labels.append(str(day_num))  # for header
            day_date = dt_date(year, month, day_num)
            self._current_day_strs.append(day_date.strftime("%Y-%m-%d"))

        self.table.setHorizontalHeaderLabels(day_labels)

        staff_inits = [s.initials for s in staff_objs]
        self._current_staff_inits = staff_inits
        self.table.setVerticalHeaderLabels(staff_inits)

        # Fix columns to ~31 px wide
        #self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        #self.table.horizontalHeader().setDefaultSectionSize(31)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 4) Build availability map + a set of holiday days
        avails = self.availability_manager.list_availability()
        availability_map = {}
        holiday_days = set()  # store just the date_str for any holiday

        for rec in avails:
            d_str = rec["date"]
            reason = rec.get("reason", "")
            # If it's a normal staff record, store by (init, date_str)
            init = rec["initials"]
            if not rec.get("is_holiday", False):
                # Normal availability => staff-based
                availability_map[(init, d_str)] = reason
            else:
                # It's a holiday => color all staff on that date
                # so store day_str in holiday_days
                holiday_days.add(d_str)

        # 5) Fill each cell with color
        for r, stf in enumerate(staff_objs):
            init = stf.initials
            for c in range(num_days):
                day_str = self._current_day_strs[c]
                # If day_str is in holiday_days => teal
                if day_str in holiday_days:
                    reason = "Holiday"
                    color = QColor("teal")
                else:
                    # normal reason from availability_map
                    reason = availability_map.get((init, day_str), "")
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
                if color is not None:
                    item.setBackground(color)
                if reason:
                    item.setToolTip(reason)

                self.table.setItem(r, c, item)

        self.table.resizeRowsToContents()

    def _on_add_availability_calendar(self):
        """Show the multi-date picking dialog (for normal PTO or partial FTE)."""
        dialog = MultiDateAvailabilityDialog(
            parent=self,
            availability_manager=self.availability_manager,
            staff_manager=self.staff_manager
        )
        if dialog.exec() == QDialog.Accepted:
            self._refresh_table()

    def _on_add_holiday(self):
        """Open the AddHolidayDialog with a single-date QCalendarWidget."""
        dialog = AddHolidayDialog(self, self.availability_manager)
        if dialog.exec() == QDialog.Accepted:
            self._refresh_table()

    def _on_remove_selected(self):
        """
        Remove the availability record from the currently selected cell.
        """
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
            QMessageBox.critical(
                self,
                "Removal Error",
                f"Could not remove availability for {staff_init}, {date_str}."
            )
