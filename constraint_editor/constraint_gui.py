# constraint_editor/constraint_gui_qt.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QPushButton, QMessageBox, QDialog, QLabel, QLineEdit,
    QDialogButtonBox, QComboBox
)
from PySide6.QtCore import Qt


class ConstraintsEditorTab(QWidget):
    """
    A PySide6 version of your old ConstraintsEditorTab.
    Replaces the Tk treeview with a QTreeWidget, plus add/edit/delete buttons.
    """

    def __init__(self, parent, constraints_manager, staff_manager, shift_manager):
        super().__init__(parent)
        self.constraints_manager = constraints_manager
        self.staff_manager = staff_manager
        self.shift_manager = shift_manager

        self.tree = None  # we'll hold a QTreeWidget reference
        self._build_ui()
        self._populate_constraint_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Tree group
        self.tree_box = QGroupBox("Constraints")
        layout.addWidget(self.tree_box)

        tree_layout = QVBoxLayout(self.tree_box)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Constraint Type", "Staff", "Shift", "Parameters"])
        tree_layout.addWidget(self.tree)

        # Buttons row
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._on_edit)
        btn_layout.addWidget(edit_btn)

        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(del_btn)

        btn_layout.addStretch(1)

    def _populate_constraint_list(self):
        """
        Clears the QTreeWidget and re-lists constraints from constraints_manager.
        """
        self.tree.clear()
        constraints = self.constraints_manager.list_constraints()
        for idx, c in enumerate(constraints):
            ctype = c.get("type", "")
            staff = c.get("staff", "")
            shift = c.get("shift", "")
            # everything else => parameters
            leftover = {k: v for k, v in c.items() if k not in ["type", "staff", "shift"]}
            param_text = str(leftover)
            item = QTreeWidgetItem([ctype, staff, shift, param_text])
            self.tree.addTopLevelItem(item)

    def _on_add(self):
        dialog = AddOrEditConstraintForm(
            parent=self,
            staff_manager=self.staff_manager,
            shift_manager=self.shift_manager,
            on_save=self._handle_new_constraint,
            initial_data=None
        )
        dialog.exec()

    def _handle_new_constraint(self, constraint_dict):
        """
        Callback from the form when user clicks OK with new constraint data.
        """
        self.constraints_manager.add_constraint(constraint_dict)
        self.constraints_manager.save_data()
        self._populate_constraint_list()
        QMessageBox.information(self, "Constraint Added", "New constraint has been added successfully.")

    def _on_edit(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.critical(self, "No Selection", "Please select a constraint to edit.")
            return
        index_in_list = self.tree.indexOfTopLevelItem(item)
        if index_in_list < 0:
            QMessageBox.critical(self, "No Selection", "Could not locate constraint index.")
            return

        existing_constraint = self.constraints_manager.list_constraints()[index_in_list]

        dialog = AddOrEditConstraintForm(
            parent=self,
            staff_manager=self.staff_manager,
            shift_manager=self.shift_manager,
            initial_data=existing_constraint,
            on_save=lambda updated: self._handle_edit_constraint(index_in_list, updated)
        )
        dialog.exec()

    def _handle_edit_constraint(self, index, updated_constraint):
        self.constraints_manager.update_constraint(index, updated_constraint)
        self.constraints_manager.save_data()
        self._populate_constraint_list()
        QMessageBox.information(self, "Constraint Updated", "Constraint updated successfully.")

    def _on_delete(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.critical(self, "No Selection", "Please select a constraint to remove.")
            return
        index_in_list = self.tree.indexOfTopLevelItem(item)
        if index_in_list < 0:
            QMessageBox.critical(self, "No Selection", "Could not locate constraint index.")
            return

        resp = QMessageBox.question(self, "Confirm Removal", "Remove this constraint?")
        if resp == QMessageBox.Yes:
            self.constraints_manager.remove_constraint(index_in_list)
            self.constraints_manager.save_data()
            self._populate_constraint_list()
            QMessageBox.information(self, "Constraint Deleted", "Constraint was removed.")


class AddOrEditConstraintForm(QDialog):
    """
    A QDialog form to let user pick: Constraint Type, Staff, Shift, and parameters.
    If initial_data is provided, we populate the fields for editing.
    on_save is called with the resulting constraint dict when the user hits OK.
    """

    def __init__(self, parent, staff_manager, shift_manager, on_save, initial_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Constraint")

        self.staff_manager = staff_manager
        self.shift_manager = shift_manager
        self.on_save = on_save
        self.initial_data = initial_data or {}

        self.constraint_types = [
            "LimitWeeklyShift",
            "AvoidBackToBack",
            "KLPreference",
            "NoBackToBackEUSFNA",
        ]

        self._build_ui()
        self._populate_initial_values()

    def _build_ui(self):
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDialogButtonBox, \
            QFormLayout

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # Constraint Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.constraint_types)
        form_layout.addRow("Constraint Type:", self.type_combo)

        # Staff
        staff_inits = [s.initials for s in self.staff_manager.list_staff()]
        self.staff_combo = QComboBox()
        self.staff_combo.addItem("")  # allow blank
        for stf in staff_inits:
            self.staff_combo.addItem(stf)
        form_layout.addRow("Staff:", self.staff_combo)

        # Shift
        shift_objs = self.shift_manager.list_shifts()
        shift_list = [sh.name for sh in shift_objs]
        self.shift_combo = QComboBox()
        self.shift_combo.addItem("")  # allow blank
        for sh_name in shift_list:
            self.shift_combo.addItem(sh_name)
        form_layout.addRow("Shift:", self.shift_combo)

        # Param1 (some generic param for demonstration)
        self.param1_edit = QLineEdit()
        form_layout.addRow("Param 1:", self.param1_edit)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.setLayout(layout)

    def _populate_initial_values(self):
        ctype = self.initial_data.get("type", "")
        staff = self.initial_data.get("staff", "")
        shift = self.initial_data.get("shift", "")

        # We'll parse leftover as param1
        leftover = {k: v for k, v in self.initial_data.items() if k not in ("type", "staff", "shift")}
        param1_value = ""
        if leftover:
            # pick first leftover key's value
            first_key = list(leftover.keys())[0]
            param1_value = leftover[first_key]

        # set combos
        idx_ctype = self.type_combo.findText(ctype)
        if idx_ctype >= 0:
            self.type_combo.setCurrentIndex(idx_ctype)

        idx_staff = self.staff_combo.findText(staff)
        if idx_staff >= 0:
            self.staff_combo.setCurrentIndex(idx_staff)

        idx_shift = self.shift_combo.findText(shift)
        if idx_shift >= 0:
            self.shift_combo.setCurrentIndex(idx_shift)

        self.param1_edit.setText(str(param1_value))

    def _on_ok(self):
        ctype = self.type_combo.currentText().strip()
        staff = self.staff_combo.currentText().strip()
        shift = self.shift_combo.currentText().strip()
        param1_value = self.param1_edit.text().strip()

        if not ctype:
            QMessageBox.critical(self, "Missing Type", "Please select a constraint type.")
            return

        constraint_dict = {
            "type": ctype,
            "staff": staff,
            "shift": shift
        }

        # Some logic for param1
        if ctype == "LimitWeeklyShift":
            # parse int?
            try:
                val = int(param1_value)
                constraint_dict["exact_count"] = val
            except ValueError:
                constraint_dict["exact_count"] = param1_value
        else:
            constraint_dict["param1"] = param1_value

        self.on_save(constraint_dict)
        self.accept()
