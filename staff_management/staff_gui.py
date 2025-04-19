# staff_management/staff_gui_qt.py

import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QGroupBox, QComboBox, QScrollBar, QAbstractItemView,
    QMessageBox, QDialog, QFormLayout, QLineEdit, QCheckBox, QDialogButtonBox,
    QFrame)
from PySide6.QtCore import Qt, QItemSelectionModel

class StaffTab(QWidget):
    """
    A PySide6 version of your StaffTab.
    Replaces Tkinter frames, lightboxes, popups, etc.
    """
    def __init__(self, parent, staff_manager, shift_manager):
        super().__init__(parent)
        self.manager = staff_manager
        self.shift_manager = shift_manager

        # This list parallels the list widget to track headings vs real staff
        self.displayed_staff = []

        self._create_ui()
        self.populate_list()

    def _create_ui(self):
        """
        Build the main layout with:
          1) A group box or frame for the staff list
          2) A horizontal area for buttons
        """
        main_layout = QVBoxLayout(self)

        # Staff List group
        staff_box = QGroupBox("Staff List")
        main_layout.addWidget(staff_box)

        staff_box_layout = QHBoxLayout(staff_box)

        self.staff_list = QListWidget()
        self.staff_list.setSelectionMode(QAbstractItemView.SingleSelection)
        staff_box_layout.addWidget(self.staff_list)

        # Buttons
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        self.add_button = QPushButton("Add Staff")
        self.add_button.clicked.connect(self.add_staff_popup)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.clicked.connect(self.edit_selected_staff)
        button_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected_staff)
        button_layout.addWidget(self.remove_button)

        # Add some stretch so buttons stay on the left
        button_layout.addStretch(1)

    def populate_list(self):
        """
        Rebuild the staff list, grouped by role with headings
        """
        self.staff_list.clear()
        self.displayed_staff = []

        staff_list = self.manager.list_staff()
        # 1) Group staff by role
        role_map = {}
        for s in staff_list:
            role_map.setdefault(s.role, []).append(s)

        # 2) Sort roles
        sorted_roles = sorted(role_map.keys())

        for role in sorted_roles:
            # Insert a heading line
            heading_item = QListWidgetItem(f"--- {role.upper()} ---")
            heading_item.setFlags(Qt.ItemIsEnabled)  # not selectable
            self.staff_list.addItem(heading_item)
            self.displayed_staff.append(None)

            # staff sorted by initials
            staff_for_role = sorted(role_map[role], key=lambda s: s.initials)

            for stf in staff_for_role:
                text = (f"{stf.initials} | "
                        f"{stf.start_time}-{stf.end_time} | "
                        f"Shifts: {', '.join(stf.trained_shifts)} | "
                        f"Constraints: {stf.constraints}")
                item = QListWidgetItem(text)
                self.staff_list.addItem(item)
                self.displayed_staff.append(stf)

            # optional blank line
            blank_item = QListWidgetItem("")
            blank_item.setFlags(Qt.ItemIsEnabled)
            self.staff_list.addItem(blank_item)
            self.displayed_staff.append(None)

    def get_selected_index(self):
        """Return the selected index or None if nothing is selected."""
        selected = self.staff_list.currentRow()
        if selected < 0 or selected >= len(self.displayed_staff):
            return None
        return selected

    # -----------------------------------------------------------
    # Add staff popup => now a QDialog
    # -----------------------------------------------------------
    def add_staff_popup(self):
        dialog = AddOrEditStaffDialog(
            parent=self,
            title="Add Staff",
            staff_obj=None,
            shift_manager=self.shift_manager,
            on_save=self._on_added_staff
        )
        dialog.exec()

    def _on_added_staff(self, staff_data):
        """
        Called after user hits OK in the add staff popup
        staff_data: dict with all fields needed to create staff
        """
        try:
            self.manager.add_staff(**staff_data)
            self.populate_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -----------------------------------------------------------
    # Edit staff
    # -----------------------------------------------------------
    def edit_selected_staff(self):
        idx = self.get_selected_index()
        if idx is None:
            QMessageBox.warning(self, "No Selection", "Please select a staff member to edit.")
            return

        staff_obj = self.displayed_staff[idx]
        if staff_obj is None:
            QMessageBox.critical(self, "Selection Error",
                "Please select an actual staff, not a heading or blank line.")
            return

        dialog = AddOrEditStaffDialog(
            parent=self,
            title=f"Edit Staff - {staff_obj.initials}",
            staff_obj=staff_obj,
            shift_manager=self.shift_manager,
            on_save=self._on_edited_staff
        )
        dialog.exec()

    def _on_edited_staff(self, staff_update):
        """
        Called after user hits OK in the edit popup
        staff_update: dict with fields for manager.edit_staff
        """
        # staff_update has "initials" plus updated role, times, etc.
        initials = staff_update["initials"]
        staff_update_clean = {k: v for k, v in staff_update.items() if k != "initials"}
        updated = self.manager.edit_staff(initials, **staff_update_clean)
        if updated:
            self.populate_list()
        else:
            QMessageBox.critical(self, "Update Failed", "Could not update staff.")

    def remove_selected_staff(self):
        idx = self.get_selected_index()
        if idx is None:
            QMessageBox.warning(self, "No Selection", "Please select a staff member to remove.")
            return

        staff_obj = self.displayed_staff[idx]
        if staff_obj is None:
            QMessageBox.critical(self, "Selection Error",
                "Please select an actual staff, not a heading or blank line.")
            return

        resp = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove staff '{staff_obj.initials}'?"
        )
        if resp == QMessageBox.Yes:
            success = self.manager.remove_staff(staff_obj.initials)
            if success:
                self.populate_list()
            else:
                QMessageBox.critical(self, "Removal Error", "Could not remove staff.")

# --------------------------------------------------------------------
# A QDialog class for "Add or Edit Staff"
# --------------------------------------------------------------------
class AddOrEditStaffDialog(QDialog):
    def __init__(self, parent, title, staff_obj, shift_manager, on_save):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.staff_obj = staff_obj
        self.shift_manager = shift_manager
        self.on_save = on_save

        self.setMinimumWidth(400)

        # Build UI
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # 1) Initials
        self.initials_edit = QLineEdit()
        if self.staff_obj:
            self.initials_edit.setText(self.staff_obj.initials)
            self.initials_edit.setReadOnly(True)  # can't change initials once set?
        form_layout.addRow("Initials:", self.initials_edit)

        # 2) Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Prep Staff", "Admin", "Cytologist"])
        if self.staff_obj:
            if self.staff_obj.role in ["Prep Staff", "Admin", "Cytologist"]:
                self.role_combo.setCurrentText(self.staff_obj.role)
        form_layout.addRow("Role:", self.role_combo)

        # 3) Start/End time
        self.start_edit = QLineEdit("09:00")
        self.end_edit = QLineEdit("17:00")
        if self.staff_obj:
            self.start_edit.setText(self.staff_obj.start_time)
            self.end_edit.setText(self.staff_obj.end_time)
        form_layout.addRow("Start Time (HH:MM):", self.start_edit)
        form_layout.addRow("End Time (HH:MM):", self.end_edit)

        # 4) Shifts by Role
        self.shifts_layout = QHBoxLayout()
        layout.addLayout(self.shifts_layout)

        # We'll build three list widgets side by side
        self.cyto_list = QListWidget()
        self.prep_list = QListWidget()
        self.admin_list = QListWidget()

        self.cyto_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.prep_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.admin_list.setSelectionMode(QAbstractItemView.MultiSelection)

        # group boxes for clarity
        cyto_box = QGroupBox("Cytologist Shifts")
        cyto_box_layout = QVBoxLayout(cyto_box)
        cyto_box_layout.addWidget(self.cyto_list)
        self.shifts_layout.addWidget(cyto_box)

        prep_box = QGroupBox("Prep Staff Shifts")
        prep_box_layout = QVBoxLayout(prep_box)
        prep_box_layout.addWidget(self.prep_list)
        self.shifts_layout.addWidget(prep_box)

        admin_box = QGroupBox("Admin Shifts")
        admin_box_layout = QVBoxLayout(admin_box)
        admin_box_layout.addWidget(self.admin_list)
        self.shifts_layout.addWidget(admin_box)

        all_shifts = self.shift_manager.list_shifts()
        # populate
        if all_shifts:
            for shift_obj in all_shifts:
                shift_name = shift_obj.name
                r = shift_obj.role_required
                if r == "Cytologist" or r == "Any":
                    item = QListWidgetItem(shift_name)
                    self.cyto_list.addItem(item)
                if r == "Prep Staff" or r == "Any":
                    item = QListWidgetItem(shift_name)
                    self.prep_list.addItem(item)
                if r == "Admin" or r == "Any":
                    item = QListWidgetItem(shift_name)
                    self.admin_list.addItem(item)

        # if editing, select the ones staff already has
        if self.staff_obj:
            for shift_name in self.staff_obj.trained_shifts:
                # find in each list
                self._select_in_list(self.cyto_list, shift_name)
                self._select_in_list(self.prep_list, shift_name)
                self._select_in_list(self.admin_list, shift_name)

        # 5) Constraints
        self.constraints_edit = QLineEdit("{}")
        half_day_default = False
        if self.staff_obj:
            # staff_obj.constraints => dict
            cdict = dict(self.staff_obj.constraints)
            if "half_day_shift" in cdict:
                half_day_default = cdict["half_day_shift"]
                del cdict["half_day_shift"]
            self.constraints_edit.setText(json.dumps(cdict))
        form_layout.addRow("Constraints (JSON):", self.constraints_edit)

        self.half_day_check = QCheckBox("Half-Shift Admin Cutoff")
        self.half_day_check.setChecked(half_day_default)
        layout.addWidget(self.half_day_check)

        # 6) Casual Status
        self.casual_check = QCheckBox("Casual Status")
        if self.staff_obj and getattr(self.staff_obj, 'is_casual', False):
            self.casual_check.setChecked(True)
        layout.addWidget(self.casual_check)

        # OK/Cancel
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _select_in_list(self, list_widget, shift_name):
        count = list_widget.count()
        for i in range(count):
            item = list_widget.item(i)
            if item.text() == shift_name:
                list_widget.setCurrentItem(item, QItemSelectionModel.Select)
                break

    def _on_ok(self):
        # gather data
        initials = self.initials_edit.text().strip()
        role = self.role_combo.currentText().strip()
        start_time = self.start_edit.text().strip()
        end_time = self.end_edit.text().strip()

        # gather new trained shifts
        selected_cyto = [self.cyto_list.item(i).text()
                         for i in range(self.cyto_list.count())
                         if self.cyto_list.item(i).isSelected()]
        selected_prep = [self.prep_list.item(i).text()
                         for i in range(self.prep_list.count())
                         if self.prep_list.item(i).isSelected()]
        selected_admin = [self.admin_list.item(i).text()
                          for i in range(self.admin_list.count())
                          if self.admin_list.item(i).isSelected()]
        trained_shifts = selected_cyto + selected_prep + selected_admin

        # parse constraints
        constraints_raw = self.constraints_edit.text().strip()
        try:
            constraints_dict = json.loads(constraints_raw) if constraints_raw else {}
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Invalid JSON", "Please enter valid JSON for constraints.")
            return

        constraints_dict["half_day_shift"] = self.half_day_check.isChecked()

        # Build final data dict
        staff_data = {
            "initials": initials,
            "role": role,
            "start_time": start_time,
            "end_time": end_time,
            "trained_shifts": trained_shifts,
            "constraints": constraints_dict,
            "is_casual": self.casual_check.isChecked()
        }

        # Call the callback
        self.on_save(staff_data)
        self.accept()  # close dialog
