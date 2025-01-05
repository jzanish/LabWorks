# shift_management/shift_gui_qt.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QPushButton, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QCheckBox, QDialogButtonBox, QLabel, QComboBox
)
from PySide6.QtCore import Qt

class ShiftTab(QWidget):
    """
    A PyQt version of your old 'ShiftTab'.
    Replaces Tkinter frames/listboxes/popups with PySide6 widgets.
    """

    def __init__(self, parent, shift_manager):
        super().__init__(parent)
        self.shift_manager = shift_manager
        self.displayed_shifts = []  # parallel list to track headings vs real shifts

        self._create_gui()
        self._refresh_shift_list()

    def _create_gui(self):
        # Main layout
        main_layout = QVBoxLayout(self)

        # Shifts group box
        shift_box = QGroupBox("Shifts")
        main_layout.addWidget(shift_box)

        shift_box_layout = QVBoxLayout(shift_box)

        # A QListWidget for shifts
        self.shift_list = QListWidget()
        shift_box_layout.addWidget(self.shift_list)

        # A horizontal layout for buttons
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        self.add_button = QPushButton("Add Shift")
        self.add_button.clicked.connect(self._open_add_shift_popup)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Shift")
        self.edit_button.clicked.connect(self._open_edit_shift_popup)
        button_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton("Remove Shift")
        self.remove_button.clicked.connect(self._remove_shift)
        button_layout.addWidget(self.remove_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_shift_list)
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch(1)

    def _refresh_shift_list(self):
        """
        Populate the QListWidget with headings for each role, followed by each shift.
        We store a parallel list 'self.displayed_shifts' to track which items are real shifts.
        """
        self.shift_list.clear()
        self.displayed_shifts = []

        all_shifts = self.shift_manager.list_shifts()
        role_map = {}
        for shift_obj in all_shifts:
            role = shift_obj.role_required if shift_obj.role_required else "Any"
            role_map.setdefault(role, []).append(shift_obj)

        inserted_roles = set()

        # Keep the order they appear in 'all_shifts'
        for shift_obj in all_shifts:
            role = shift_obj.role_required if shift_obj.role_required else "Any"
            if role not in inserted_roles:
                # Insert a heading line
                heading_text = f"--- {role.upper()} ---"
                heading_item = QListWidgetItem(heading_text)
                heading_item.setFlags(Qt.ItemIsEnabled)  # not selectable
                self.shift_list.addItem(heading_item)
                self.displayed_shifts.append(None)
                inserted_roles.add(role)

                # Insert each shift in that role
                for s in role_map[role]:
                    display_text = (
                        f"{s.name} | "
                        f"Flexible={s.is_flexible} | "
                        f"Open={s.can_remain_open} | "
                        f"Start={s.start_time} | "
                        f"End={s.end_time}"
                    )
                    shift_item = QListWidgetItem(display_text)
                    self.shift_list.addItem(shift_item)
                    self.displayed_shifts.append(s)

                # Blank line
                blank_item = QListWidgetItem("")
                blank_item.setFlags(Qt.ItemIsEnabled)
                self.shift_list.addItem(blank_item)
                self.displayed_shifts.append(None)

    def _get_selected_index(self):
        row = self.shift_list.currentRow()
        if row < 0 or row >= len(self.displayed_shifts):
            return None
        return row

    def _open_add_shift_popup(self):
        dialog = ShiftEditDialog(
            parent=self,
            title="Add Shift",
            shift_obj=None,
            on_save=self._on_added_shift
        )
        dialog.exec()

    def _on_added_shift(self, shift_data):
        # 'shift_data' is a dict with all fields needed by shift_manager.add_shift
        self.shift_manager.add_shift(**shift_data)
        self._refresh_shift_list()

    def _open_edit_shift_popup(self):
        idx = self._get_selected_index()
        if idx is None:
            QMessageBox.critical(self, "Selection Error", "Please select a shift to edit.")
            return

        shift_obj = self.displayed_shifts[idx]
        if shift_obj is None:
            QMessageBox.critical(
                self, "Selection Error",
                "Please select an actual shift, not a heading or blank line."
            )
            return

        dialog = ShiftEditDialog(
            parent=self,
            title="Edit Shift",
            shift_obj=shift_obj,
            on_save=self._on_edited_shift
        )
        dialog.exec()

    def _on_edited_shift(self, shift_update):
        # shift_update has old_name plus the updates
        old_name = shift_update.pop("old_name")
        self.shift_manager.edit_shift(old_name, **shift_update)
        self._refresh_shift_list()

    def _remove_shift(self):
        idx = self._get_selected_index()
        if idx is None:
            QMessageBox.critical(self, "Selection Error", "Please select a shift to remove.")
            return

        shift_obj = self.displayed_shifts[idx]
        if shift_obj is None:
            QMessageBox.critical(
                self, "Selection Error",
                "Please select an actual shift, not a heading or blank line."
            )
            return

        resp = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove shift '{shift_obj.name}'?"
        )
        if resp == QMessageBox.Yes:
            self.shift_manager.remove_shift(shift_obj.name)
            self._refresh_shift_list()

# ----------------------------------------------------------------------
# Dialog for adding or editing a Shift
# ----------------------------------------------------------------------
class ShiftEditDialog(QDialog):
    def __init__(self, parent, title, shift_obj, on_save):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.shift_obj = shift_obj
        self.on_save = on_save

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        layout.addLayout(form)

        # Shift Name
        self.name_edit = QLineEdit()
        form.addRow("Shift Name:", self.name_edit)

        # Role Required
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Any", "Prep Staff", "Admin", "Cytologist"])
        form.addRow("Role Required:", self.role_combo)

        self.is_flexible_check = QCheckBox("Flexible Shift")
        layout.addWidget(self.is_flexible_check)

        self.can_remain_open_check = QCheckBox("Can Remain Open")
        layout.addWidget(self.can_remain_open_check)

        # Start/End time
        self.start_edit = QLineEdit()
        form.addRow("Start Time (HH:MM):", self.start_edit)

        self.end_edit = QLineEdit()
        form.addRow("End Time (HH:MM):", self.end_edit)

        # Days of Week
        days_label = QLabel("Days of Week Needed:")
        layout.addWidget(days_label)

        self.days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.days_vars = {}
        days_layout = QHBoxLayout()
        layout.addLayout(days_layout)

        for day in self.days_list:
            var = QCheckBox(day)
            days_layout.addWidget(var)
            self.days_vars[day] = var

        # Button box
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # If editing, populate fields
        if self.shift_obj:
            self.name_edit.setText(self.shift_obj.name)
            if self.shift_obj.role_required in ["Any", "Prep Staff", "Admin", "Cytologist"]:
                self.role_combo.setCurrentText(self.shift_obj.role_required)
            self.is_flexible_check.setChecked(self.shift_obj.is_flexible)
            self.can_remain_open_check.setChecked(self.shift_obj.can_remain_open)
            if self.shift_obj.start_time:
                self.start_edit.setText(self.shift_obj.start_time)
            if self.shift_obj.end_time:
                self.end_edit.setText(self.shift_obj.end_time)

            # days_of_week
            for d in getattr(self.shift_obj, 'days_of_week', []):
                if d in self.days_vars:
                    self.days_vars[d].setChecked(True)

    def _on_ok(self):
        shift_name = self.name_edit.text().strip()
        role_req = self.role_combo.currentText().strip()
        is_flexible = self.is_flexible_check.isChecked()
        can_open = self.can_remain_open_check.isChecked()
        start_t = self.start_edit.text().strip() or None
        end_t = self.end_edit.text().strip() or None

        selected_days = []
        for d in self.days_list:
            if self.days_vars[d].isChecked():
                selected_days.append(d)

        if not shift_name:
            QMessageBox.critical(self, "Validation Error", "Shift name is required.")
            return

        # Build a dict for on_save
        shift_data = {
            "name": shift_name,
            "role_required": role_req,
            "is_flexible": is_flexible,
            "can_remain_open": can_open,
            "start_time": start_t,
            "end_time": end_t,
            "days_of_week": selected_days
        }

        if self.shift_obj:
            # We'll pass the old_name so we can do shift_manager.edit_shift(old_name, **updates)
            shift_data["old_name"] = self.shift_obj.name

        self.on_save(shift_data)
        self.accept()
