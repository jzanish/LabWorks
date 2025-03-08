# shift_filter_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QAbstractItemView, QDialogButtonBox, QLabel
)
from PySide6.QtCore import Qt

class ShiftFilterDialog(QDialog):
    """
    A dialog that lists all possible shift names, letting user multi-select
    which shifts to include in the bar chart.
    """
    def __init__(self, parent, all_shift_names):
        super().__init__(parent)
        self.setWindowTitle("Select Shifts to Graph")

        self.all_shift_names = sorted(all_shift_names)
        self._selected_shifts = set()

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Select which shifts to include in the bar chart:")
        layout.addWidget(label)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.list_widget)

        # Populate
        for sname in self.all_shift_names:
            item = QListWidgetItem(sname)
            self.list_widget.addItem(item)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_ok(self):
        # gather selected items
        selected_items = self.list_widget.selectedItems()
        self._selected_shifts = {it.text() for it in selected_items}
        self.accept()

    def get_selected_shifts(self):
        """Returns a set of shift names the user selected."""
        return self._selected_shifts
