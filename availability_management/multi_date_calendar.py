# multi_date_calendar.py

from PySide6.QtWidgets import (
    QCalendarWidget, QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox,
    QMessageBox, QComboBox, QFormLayout, QGroupBox, QRadioButton, QHBoxLayout, QVBoxLayout
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QTextCharFormat, QColor
from datetime import date

class MultiSelectCalendar(QCalendarWidget):
    """
    A QCalendarWidget that supports toggling multiple arbitrary dates.
    Each time a date is clicked, we highlight or un-highlight it and store it in a set.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_dates = set()

        # Format used to highlight selected cells (Blue background).
        self._highlight_format = QTextCharFormat()
        self._highlight_format.setBackground(QColor("Blue"))

        # Connect QCalendarWidget's clicked signal.
        self.clicked.connect(self._on_date_clicked)

    def _on_date_clicked(self, qdate):
        """
        Toggle date in/out of our selected set, then highlight or clear it.
        """
        pydate = date(qdate.year(), qdate.month(), qdate.day())

        if pydate in self._selected_dates:
            # Unselect
            self._selected_dates.remove(pydate)
            self.setDateTextFormat(qdate, QTextCharFormat())  # clear highlight
        else:
            # Select
            self._selected_dates.add(pydate)
            self.setDateTextFormat(qdate, self._highlight_format)

    def get_selected_dates(self):
        """
        Return a sorted list of the selected Python date objects.
        """
        return sorted(self._selected_dates)

    def clear_selection(self):
        """
        Unselect all currently highlighted dates.
        """
        for d in self._selected_dates:
            qd = QDate(d.year, d.month, d.day)
            self.setDateTextFormat(qd, QTextCharFormat())
        self._selected_dates.clear()


class MultiDateAvailabilityDialog(QDialog):
    """
    A dialog that shows:
      - A combo box for Staff
      - A multi-select calendar for picking multiple days
      - Radio buttons for reason (PTO, 0.5 FTE, 0.8 FTE, SSL, Other).
      - If "Other" is chosen, a text field to type a custom reason.
    On OK, we commit the chosen dates to the availability_manager.
    """
    def __init__(self, parent=None, availability_manager=None, staff_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Select Multiple Dates")
        self.resize(800, 600)
        self.availability_manager = availability_manager
        self.staff_manager = staff_manager

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 1) The custom multi-date calendar
        self.calendar = MultiSelectCalendar(self)
        layout.addWidget(self.calendar)

        # 2) A form layout for staff selection
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # Staff Combo Box
        self.staff_combo = QComboBox()
        if self.staff_manager:
            staff_objs = self.staff_manager.list_staff()
            all_inits = sorted(s.initials for s in staff_objs)  # Sort in-place alphabetically
            for init in all_inits:
                self.staff_combo.addItem(init)
        form_layout.addRow("Staff:", self.staff_combo)

        # 3) A group box for reason radio buttons
        reason_group = QGroupBox("Reason")
        reason_layout = QHBoxLayout(reason_group)
        layout.addWidget(reason_group)

        # Create radio buttons
        self.radio_pto = QRadioButton("PTO")
        self.radio_pto.setChecked(True)  # default
        self.radio_half = QRadioButton("0.5 FTE")
        self.radio_eight = QRadioButton("0.8 FTE")
        self.radio_ssl = QRadioButton("SSL")
        self.radio_other = QRadioButton("Other:")

        reason_layout.addWidget(self.radio_pto)
        reason_layout.addWidget(self.radio_half)
        reason_layout.addWidget(self.radio_eight)
        reason_layout.addWidget(self.radio_ssl)
        reason_layout.addWidget(self.radio_other)

        # 4) A text field for "Other" reason, disabled by default
        self.other_line = QLineEdit()
        self.other_line.setPlaceholderText("Specify if 'Other'")
        self.other_line.setEnabled(False)
        reason_layout.addWidget(self.other_line)

        # Connect toggles so we can enable/disable other_line
        self.radio_pto.toggled.connect(self._on_radio_toggled)
        self.radio_half.toggled.connect(self._on_radio_toggled)
        self.radio_eight.toggled.connect(self._on_radio_toggled)
        self.radio_ssl.toggled.connect(self._on_radio_toggled)
        self.radio_other.toggled.connect(self._on_radio_toggled)

        # 5) OK/Cancel
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_radio_toggled(self):
        """
        Enable the 'other_line' only if radio_other is checked.
        """
        if self.radio_other.isChecked():
            self.other_line.setEnabled(True)
        else:
            self.other_line.setEnabled(False)
            self.other_line.clear()

    def _on_ok(self):
        """
        On OK, gather staff, reason, selected dates, commit them to availability_manager.
        """
        # Staff
        staff_init = self.staff_combo.currentText().strip()
        if not staff_init:
            QMessageBox.critical(self, "Validation Error", "No staff selected!")
            return

        # Dates
        selected_dates = self.calendar.get_selected_dates()
        if not selected_dates:
            QMessageBox.warning(self, "No Dates", "Please select at least one date.")
            return

        # Reason
        if self.radio_pto.isChecked():
            reason = "PTO"
        elif self.radio_half.isChecked():
            reason = "0.5 FTE"
        elif self.radio_eight.isChecked():
            reason = "0.8 FTE"
        elif self.radio_ssl.isChecked():
            reason = "SSL"
        elif self.radio_other.isChecked():
            typed = self.other_line.text().strip()
            if not typed:
                QMessageBox.critical(self, "Validation Error", "Please specify the 'Other' reason.")
                return
            reason = typed
        else:
            # Should not happen, but just in case no radio is selected
            QMessageBox.critical(self, "Validation Error", "Please pick a reason.")
            return

        # Add them all
        if self.availability_manager:
            for d in selected_dates:
                date_str = d.isoformat()  # "YYYY-MM-DD"
                self.availability_manager.add_availability(staff_init, date_str, reason)

        self.accept()
