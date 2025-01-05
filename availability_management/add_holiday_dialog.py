# availability_management/add_holiday_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QMessageBox
)


class AddHolidayDialog(QDialog):
    """
    A QDialog for adding a holiday date (YYYY-MM-DD),
    automatically setting is_holiday=True.
    """

    def __init__(self, parent, availability_manager):
        super().__init__(parent)
        self.setWindowTitle("Add Holiday")
        self.availability_manager = availability_manager

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Form for date + reason
        form = QFormLayout()
        layout.addLayout(form)

        # Date input
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("YYYY-MM-DD")
        form.addRow("Holiday Date:", self.date_edit)

        # Reason field (default "Holiday")
        self.reason_edit = QLineEdit("Holiday")
        form.addRow("Reason (optional):", self.reason_edit)

        # OK/Cancel
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_ok(self):
        date_str = self.date_edit.text().strip()
        reason = self.reason_edit.text().strip()

        if not date_str:
            QMessageBox.critical(self, "Validation Error", "Holiday date is required.")
            return

        # Build the record with is_holiday=True
        record = {
            "initials": "ALL",  # or "HOLIDAY" if you prefer
            "date": date_str,
            "reason": reason,
            "is_holiday": True
        }
        self.availability_manager.add_record(record)
        self.accept()
