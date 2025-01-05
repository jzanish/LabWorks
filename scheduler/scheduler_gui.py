# scheduler/scheduler_gui.py

import sys
import json
import os
from datetime import datetime, date, timedelta
from io import StringIO

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QListWidget, QListWidgetItem, QComboBox, QLineEdit, QDialog, QDialogButtonBox,
    QMessageBox, QCheckBox, QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QDateEdit
)
from PySide6.QtCore import Qt, QDate

SCHEDULER_ORDER_FILE = "data/scheduler_order.json"
EBUS_FRIDAYS_FILE = "data/ebus_fridays.json"


# ----------------------------------------------------------------
# Replaces the old DualReorderDialog
# ----------------------------------------------------------------
class DualReorderDialog(QDialog):
    """
    Dialog for reordering staff & shifts side by side (two list widgets).
    """

    def __init__(self, parent, title, staff_items, shift_items, callback):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.callback = callback

        self.staff_list = list(staff_items)
        self.shift_list = list(shift_items)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # A horizontal layout for staff vs shift
        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        # Left side: Staff reorder
        staff_box = QGroupBox("Staff Order")
        top_layout.addWidget(staff_box)

        staff_box_layout = QHBoxLayout(staff_box)

        from PySide6.QtWidgets import QListWidget
        self.staff_listwidget = QListWidget()
        staff_box_layout.addWidget(self.staff_listwidget)

        staff_btn_layout = QVBoxLayout()
        staff_box_layout.addLayout(staff_btn_layout)

        up_staff_btn = QPushButton("Up")
        up_staff_btn.clicked.connect(self._staff_move_up)
        staff_btn_layout.addWidget(up_staff_btn)

        down_staff_btn = QPushButton("Down")
        down_staff_btn.clicked.connect(self._staff_move_down)
        staff_btn_layout.addWidget(down_staff_btn)

        staff_btn_layout.addStretch(1)

        # Right side: Shift reorder
        shift_box = QGroupBox("Shift Order")
        top_layout.addWidget(shift_box)

        shift_box_layout = QHBoxLayout(shift_box)

        self.shift_listwidget = QListWidget()
        shift_box_layout.addWidget(self.shift_listwidget)

        shift_btn_layout = QVBoxLayout()
        shift_box_layout.addLayout(shift_btn_layout)

        up_shift_btn = QPushButton("Up")
        up_shift_btn.clicked.connect(self._shift_move_up)
        shift_btn_layout.addWidget(up_shift_btn)

        down_shift_btn = QPushButton("Down")
        down_shift_btn.clicked.connect(self._shift_move_down)
        shift_btn_layout.addWidget(down_shift_btn)

        shift_btn_layout.addStretch(1)

        # Bottom: OK/Cancel
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

        self._populate_listwidgets()

    def _populate_listwidgets(self):
        self.staff_listwidget.clear()
        for item in self.staff_list:
            self.staff_listwidget.addItem(item)

        self.shift_listwidget.clear()
        for item in self.shift_list:
            self.shift_listwidget.addItem(item)

    def _staff_move_up(self):
        row = self.staff_listwidget.currentRow()
        if row <= 0:
            return
        self.staff_list[row], self.staff_list[row - 1] = self.staff_list[row - 1], self.staff_list[row]
        self._populate_listwidgets()
        self.staff_listwidget.setCurrentRow(row - 1)

    def _staff_move_down(self):
        row = self.staff_listwidget.currentRow()
        if row < 0 or row >= len(self.staff_list) - 1:
            return
        self.staff_list[row], self.staff_list[row + 1] = self.staff_list[row + 1], self.staff_list[row]
        self._populate_listwidgets()
        self.staff_listwidget.setCurrentRow(row + 1)

    def _shift_move_up(self):
        row = self.shift_listwidget.currentRow()
        if row <= 0:
            return
        self.shift_list[row], self.shift_list[row - 1] = self.shift_list[row - 1], self.shift_list[row]
        self._populate_listwidgets()
        self.shift_listwidget.setCurrentRow(row - 1)

    def _shift_move_down(self):
        row = self.shift_listwidget.currentRow()
        if row < 0 or row >= len(self.shift_list) - 1:
            return
        self.shift_list[row], self.shift_list[row + 1] = self.shift_list[row + 1], self.shift_list[row]
        self._populate_listwidgets()
        self.shift_listwidget.setCurrentRow(row + 1)

    def _on_ok(self):
        self.callback(self.staff_list, self.shift_list)
        self.accept()


# ----------------------------------------------------------------
# Replaces the old ManualAssignmentDialog
# ----------------------------------------------------------------
class ManualAssignmentDialog(QDialog):
    """
    A dialog for manually assigning staff to shifts in a day/shift grid.
    Also pre-populates from existing preassignments.
    """
    def __init__(self, parent, title, day_list, shift_list, staff_list, callback, existing_preassigned=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.callback = callback
        self.day_list = day_list
        self.shift_list = shift_list
        self.staff_list = staff_list
        self.existing_preassigned = existing_preassigned or {}

        self.cell_widgets = {}

        self._build_ui()
        self._populate_existing_assignments()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top_frame = QWidget()
        layout.addWidget(top_frame)

        from PySide6.QtWidgets import QGridLayout, QLabel, QComboBox
        self.grid = QGridLayout(top_frame)

        # corner
        corner_lbl = QLabel("Shift \\ Day")
        self.grid.addWidget(corner_lbl, 0, 0)

        import datetime as dt
        for d_idx, d_str in enumerate(self.day_list):
            d_obj = dt.datetime.strptime(d_str, "%Y-%m-%d")
            heading_text = d_obj.strftime("%a %d")
            lbl = QLabel(heading_text)
            lbl.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(lbl, 0, d_idx + 1)

        for s_idx, shift_name in enumerate(self.shift_list):
            row_index = s_idx + 1
            shift_lbl = QLabel(shift_name)
            self.grid.addWidget(shift_lbl, row_index, 0)

            for d_idx, d_str in enumerate(self.day_list):
                combo = QComboBox()
                combo.addItem("None")
                for stf in self.staff_list:
                    combo.addItem(stf)
                self.grid.addWidget(combo, row_index, d_idx + 1)
                self.cell_widgets[(d_str, shift_name)] = combo

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # column stretch so combos expand
        col_count = len(self.day_list) + 1
        for c in range(col_count):
            self.grid.setColumnStretch(c, 1)

    def _populate_existing_assignments(self):
        for (d_str, shift_name), staff_init in self.existing_preassigned.items():
            combo = self.cell_widgets.get((d_str, shift_name))
            if combo:
                # If staff_init not in combo, add it
                found = False
                for i in range(combo.count()):
                    if combo.itemText(i) == staff_init:
                        found = True
                        combo.setCurrentText(staff_init)
                        break
                if not found and staff_init != "None":
                    combo.addItem(staff_init)
                    combo.setCurrentText(staff_init)

    def _on_ok(self):
        preassigned = {}
        for key, combo in self.cell_widgets.items():
            chosen = combo.currentText()
            if chosen and chosen != "None":
                preassigned[key] = chosen
        self.callback(preassigned)
        self.accept()


# ----------------------------------------------------------------
# Replaces the old EbusFridayDialog
# ----------------------------------------------------------------
class EbusFridayDialog(QDialog):
    """
    Manage which Fridays are considered EBUS Fridays.
    """
    def __init__(self, parent, ebus_list, callback_save):
        super().__init__(parent)
        self.setWindowTitle("Manage EBUS Fridays")
        self.callback_save = callback_save
        self.ebus_dates = set(ebus_list)

        self._build_ui()
        self._populate_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("List of EBUS Fridays (YYYY-MM-DD):")
        layout.addWidget(label)

        from PySide6.QtWidgets import QListWidget, QLineEdit, QPushButton, QDialogButtonBox, QHBoxLayout
        self.listwidget = QListWidget()
        layout.addWidget(self.listwidget)

        entry_layout = QHBoxLayout()
        layout.addLayout(entry_layout)

        self.new_date_edit = QLineEdit()
        self.new_date_edit.setPlaceholderText("YYYY-MM-DD")
        entry_layout.addWidget(self.new_date_edit)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._on_add)
        entry_layout.addWidget(add_btn)

        rm_btn = QPushButton("Remove Selected")
        rm_btn.clicked.connect(self._on_remove)
        layout.addWidget(rm_btn)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _populate_list(self):
        self.listwidget.clear()
        for date_str in sorted(self.ebus_dates):
            self.listwidget.addItem(date_str)

    def _on_add(self):
        date_str = self.new_date_edit.text().strip()
        if not date_str:
            return
        from datetime import datetime
        try:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            QMessageBox.critical(self, "Invalid Date", "Date must be YYYY-MM-DD format.")
            return
        if dt_obj.weekday() != 4:
            resp = QMessageBox.question(self, "Non-Friday", "This date is not a Friday. Are you sure?")
            if resp != QMessageBox.Yes:
                return
        if date_str not in self.ebus_dates:
            self.ebus_dates.add(date_str)
            self._populate_list()
        self.new_date_edit.clear()

    def _on_remove(self):
        item = self.listwidget.currentItem()
        if not item:
            return
        date_str = item.text()
        self.ebus_dates.discard(date_str)
        self._populate_list()

    def _on_ok(self):
        final_list = sorted(self.ebus_dates)
        self.callback_save(final_list)
        self.accept()


# ----------------------------------------------------------------
# The main SchedulerTab replaced by a PyQt widget
# with QDateEdit pickers for Start and End date
# + the missing create_* methods
# ----------------------------------------------------------------
class SchedulerTab(QWidget):
    def __init__(self, parent, ortools_scheduler, staff_manager, review_manager=None):
        super().__init__(parent)
        self.ortools_scheduler = ortools_scheduler
        self.staff_manager = staff_manager
        self.review_manager = review_manager

        self.last_generated_schedule = None
        self.role_order = ["Cytologist", "Admin", "Prep Staff", "Unscheduled"]
        self._preassigned = {}

        self.staff_order, self.shift_order = self._load_orders_from_file()
        self.ebus_fridays = self._load_ebus_fridays()

        main_layout = QVBoxLayout(self)

        # SHIFT-based table
        self.bench_box = QGroupBox("Shift-Based Assignments")
        main_layout.addWidget(self.bench_box)
        self.bench_box_layout = QVBoxLayout(self.bench_box)

        # STAFF-based table
        self.role_box = QGroupBox("Role-Based Schedule")
        main_layout.addWidget(self.role_box)
        self.role_box_layout = QVBoxLayout(self.role_box)

        # Input Layout (for date pickers + Generate + Send to Review)
        self.input_layout = QHBoxLayout()
        main_layout.addLayout(self.input_layout)
        self._create_input_ui(self.input_layout)

        # Reorder / Manual / EBUS row
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)
        self._create_reorder_button(button_layout)
        self._create_manual_assign_button(button_layout)
        self._create_ebus_button(button_layout)
        button_layout.addStretch(1)

        # SHIFT→Clipboard / STAFF→Clipboard
        export_layout = QHBoxLayout()
        main_layout.addLayout(export_layout)
        shift_clip_btn = QPushButton("SHIFT → Clipboard")
        shift_clip_btn.clicked.connect(self._copy_bench_clipboard)
        export_layout.addWidget(shift_clip_btn)

        staff_clip_btn = QPushButton("STAFF → Clipboard")
        staff_clip_btn.clicked.connect(self._copy_role_clipboard)
        export_layout.addWidget(staff_clip_btn)
        export_layout.addStretch(1)

        # Load staff from manager
        self._load_staff_order_from_manager()

    # -------------- Input UI (date pickers, generate, review) --------------
    def _create_input_ui(self, layout):
        layout.addWidget(QLabel("Start Date:"))

        # QDateEdit for start date
        self.start_dateedit = QDateEdit()
        self.start_dateedit.setDate(QDate(2025, 1, 6))  # default
        self.start_dateedit.setCalendarPopup(True)
        self.start_dateedit.dateChanged.connect(self._auto_set_end_date)
        layout.addWidget(self.start_dateedit)

        layout.addWidget(QLabel("End Date:"))
        self.end_dateedit = QDateEdit()
        self.end_dateedit.setDate(QDate(2025, 1, 10))
        self.end_dateedit.setCalendarPopup(True)
        layout.addWidget(self.end_dateedit)

        gen_btn = QPushButton("Generate Schedule")
        gen_btn.clicked.connect(self.generate_schedule)
        layout.addWidget(gen_btn)

        review_btn = QPushButton("Send to Schedule Review →")
        review_btn.clicked.connect(self._on_send_to_review)
        layout.addWidget(review_btn)

        layout.addStretch(1)

    def _auto_set_end_date(self, qdate):
        """
        Called whenever the user picks a new start date.
        We'll set the End Date to the Friday of that same week.
        """
        dt_s = date(qdate.year(), qdate.month(), qdate.day())
        offset = (4 - dt_s.weekday()) % 7
        dt_end = dt_s + timedelta(days=offset)

        new_qdate = QDate(dt_end.year, dt_end.month, dt_end.day)
        self.end_dateedit.setDate(new_qdate)
    # -------------- Reorder Button + method --------------
    def _create_reorder_button(self, parent_layout):
        reorder_btn = QPushButton("Reorder Staff & Shifts")
        reorder_btn.clicked.connect(self._open_reorder_dialog)
        parent_layout.addWidget(reorder_btn)

    def _open_reorder_dialog(self):
        def reorder_callback(new_staff_list, new_shift_list):
            self.staff_order = new_staff_list
            self.shift_order = new_shift_list
            self._save_orders_to_file()
            QMessageBox.information(self, "Order Updated", "Staff & shift order updated successfully!")
            self._refresh_schedule_display()

        dialog = DualReorderDialog(
            self,
            "Reorder Staff & Shifts",
            self.staff_order,
            self.shift_order,
            reorder_callback
        )
        dialog.exec()

    # -------------- Manual Assignments Button + method --------------
    def _create_manual_assign_button(self, parent_layout):
        assign_btn = QPushButton("Manual Assignments")
        assign_btn.clicked.connect(self._open_manual_dialog)
        parent_layout.addWidget(assign_btn)

    def _open_manual_dialog(self):
        # parse QDateEdit -> python date
        dt_s = date(self.start_dateedit.date().year(),
                    self.start_dateedit.date().month(),
                    self.start_dateedit.date().day())
        dt_e = date(self.end_dateedit.date().year(),
                    self.end_dateedit.date().month(),
                    self.end_dateedit.date().day())

        if dt_e < dt_s:
            QMessageBox.critical(self, "Invalid Date", "End date cannot be before start date.")
            return

        day_list = []
        cursor = dt_s
        while cursor <= dt_e:
            if cursor.weekday() < 5:
                day_list.append(cursor.strftime("%Y-%m-%d"))
            cursor += timedelta(days=1)

        all_shifts = self.ortools_scheduler.shift_manager.list_shifts()
        shift_name_map = {sh.name: sh for sh in all_shifts}
        shift_ordered = [sh for sh in self.shift_order if sh in shift_name_map]
        leftover_shifts = [sh for sh in shift_name_map.keys() if sh not in shift_ordered]
        final_shifts = shift_ordered + leftover_shifts

        staff_objs = self.staff_manager.list_staff()
        staff_inits = [s_obj.initials for s_obj in staff_objs]

        def on_ok(preassigned_dict):
            self._preassigned.update(preassigned_dict)
            QMessageBox.information(self, "Manual Assignments", "Your manual picks have been stored.")
            self.generate_schedule()

        dialog = ManualAssignmentDialog(
            self,
            "Manual Assignments",
            day_list,
            final_shifts,
            staff_inits,
            on_ok,
            existing_preassigned=self._preassigned
        )
        dialog.exec()

    # -------------- EBUS Button + method --------------
    def _create_ebus_button(self, parent_layout):
        ebus_btn = QPushButton("Manage EBUS Fridays")
        ebus_btn.clicked.connect(self._open_ebus_dialog)
        parent_layout.addWidget(ebus_btn)

    def _open_ebus_dialog(self):
        def save_ebus_list(new_list):
            self.ebus_fridays = new_list
            self._save_ebus_fridays()
            QMessageBox.information(self, "EBUS Fridays Updated",
                                    "List of EBUS Fridays was updated and saved.")

        dialog = EbusFridayDialog(self, self.ebus_fridays, save_ebus_list)
        dialog.exec()

    # -------------- Generate the schedule --------------
    def generate_schedule(self):
        self._load_staff_order_from_manager()

        dt_s = date(self.start_dateedit.date().year(),
                    self.start_dateedit.date().month(),
                    self.start_dateedit.date().day())
        dt_e = date(self.end_dateedit.date().year(),
                    self.end_dateedit.date().month(),
                    self.end_dateedit.date().day())

        if dt_e < dt_s:
            QMessageBox.critical(self, "Invalid Date", "End date cannot be before start date.")
            return

        start_date_str = dt_s.strftime("%Y-%m-%d")
        end_date_str = dt_e.strftime("%Y-%m-%d")

        # Check EBUS
        is_ebus_friday = False
        cursor = dt_s
        while cursor <= dt_e:
            if cursor.weekday() == 4:  # Friday
                if cursor.strftime("%Y-%m-%d") in self.ebus_fridays:
                    is_ebus_friday = True
                    break
            cursor += timedelta(days=1)

        schedule_data = self.ortools_scheduler.generate_schedule(
            start_date_str,
            end_date_str,
            preassigned=self._preassigned,
            is_ebus_friday=is_ebus_friday
        )
        if not schedule_data:
            QMessageBox.information(self, "No Schedule", "No feasible solution or empty schedule.")
            return

        self.last_generated_schedule = schedule_data

        # Clear old SHIFT/ROLE widgets
        for i in reversed(range(self.bench_box_layout.count())):
            w = self.bench_box_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        for i in reversed(range(self.role_box_layout.count())):
            w = self.role_box_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        self._build_bench_table(schedule_data)
        self._build_role_table(schedule_data)

        QMessageBox.information(self, "Schedule Generated", "Schedule generated successfully!")

    # -------------- Send to Schedule Review --------------
    def _on_send_to_review(self):
        if not self.last_generated_schedule:
            QMessageBox.warning(self, "No Schedule", "Please generate a schedule before sending to review.")
            return

        dt_s = date(self.start_dateedit.date().year(),
                    self.start_dateedit.date().month(),
                    self.start_dateedit.date().day())
        dt_e = date(self.end_dateedit.date().year(),
                    self.end_dateedit.date().month(),
                    self.end_dateedit.date().day())

        start_date_str = dt_s.strftime("%Y-%m-%d")
        end_date_str = dt_e.strftime("%Y-%m-%d")

        schedule_data = {
            "start_date": start_date_str,
            "end_date": end_date_str,
            "assignments": self.last_generated_schedule,
            "created_at": datetime.now().isoformat()
        }

        if self.review_manager:
            self.review_manager.commit_schedule(schedule_data)
            QMessageBox.information(
                self, "Schedule Review",
                f"Schedule sent to review successfully!\nFile saved for {start_date_str} → {end_date_str}."
            )
        else:
            QMessageBox.critical(self, "No Review Manager",
                                 "No review_manager is attached to the SchedulerTab!")

    # -------------- SHIFT x DAY Table --------------
    def _build_bench_table(self, schedule_data):
        bench_tree = QTreeWidget()
        bench_tree.setColumnCount(1 + len(schedule_data.keys()))
        day_list = self._date_range(schedule_data)
        columns = ["Shift"] + day_list
        bench_tree.setHeaderLabels(columns)

        shift_map = {}
        for day_str, assigns in schedule_data.items():
            for rec in assigns:
                shift_name = rec["shift"]
                staff_init = rec["assigned_to"]
                if shift_name not in shift_map:
                    shift_map[shift_name] = {}
                shift_map[shift_name][day_str] = staff_init

        shift_in_schedule = list(shift_map.keys())
        shift_ordered = [sh for sh in self.shift_order if sh in shift_in_schedule]
        leftover_shifts = [sh for sh in shift_in_schedule if sh not in shift_ordered]
        shift_ordered += leftover_shifts

        for sh_name in shift_ordered:
            if sh_name not in shift_map:
                continue
            day_dict = shift_map[sh_name]

            row_data = [sh_name]
            for d in day_list:
                assigned = day_dict.get(d, "")
                if assigned == "Unassigned":
                    assigned = ""
                row_data.append(assigned)

            item = QTreeWidgetItem(row_data)
            bench_tree.addTopLevelItem(item)

        bench_tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.bench_box_layout.addWidget(bench_tree)

    # -------------- STAFF x DAY Table --------------
    def _build_role_table(self, schedule_data):
        role_tree = QTreeWidget()
        day_list = self._date_range(schedule_data)
        columns = ["Staff (Role)"] + day_list
        role_tree.setColumnCount(len(columns))
        role_tree.setHeaderLabels(columns)

        role_map = {}
        staff_role_map = {}

        all_staff_objs = self.staff_manager.list_staff()
        for s_obj in all_staff_objs:
            r = s_obj.role if s_obj.role in ["Cytologist", "Admin", "Prep Staff"] else "Unscheduled"
            staff_role_map[s_obj.initials] = r

        for day_str, assigns in schedule_data.items():
            for rec in assigns:
                shift_name = rec["shift"]
                staff_init = rec["assigned_to"]
                if staff_init == "Unassigned":
                    continue
                schedule_role = rec.get("role", None)
                if not schedule_role or schedule_role == "Unknown":
                    schedule_role = staff_role_map.get(staff_init, "Unscheduled")

                if schedule_role not in role_map:
                    role_map[schedule_role] = {}
                if staff_init not in role_map[schedule_role]:
                    role_map[schedule_role][staff_init] = {}
                role_map[schedule_role][staff_init][day_str] = shift_name

        for s_init, r in staff_role_map.items():
            if r not in role_map:
                role_map[r] = {}
            if s_init not in role_map[r]:
                role_map[r][s_init] = {}

        roles_in_schedule = list(role_map.keys())
        role_ordered = [r for r in self.role_order if r in roles_in_schedule]
        leftover_roles = [r for r in roles_in_schedule if r not in role_ordered]
        role_ordered += leftover_roles

        for role in role_ordered:
            heading_item = QTreeWidgetItem([role] + [""] * len(day_list))
            heading_item.setData(0, Qt.UserRole, "role_heading")
            role_tree.addTopLevelItem(heading_item)

            staff_map = role_map[role]
            staff_in_this_role = list(staff_map.keys())

            staff_ordered = [init for init in self.staff_order if init in staff_in_this_role]
            leftover_staff = [init for init in staff_in_this_role if init not in staff_ordered]
            staff_ordered += leftover_staff

            for s_init in staff_ordered:
                day_dict = staff_map[s_init]
                row_vals = [s_init]
                for d in day_list:
                    shift_assigned = day_dict.get(d, "")
                    row_vals.append(shift_assigned)
                item = QTreeWidgetItem(row_vals)
                heading_item.addChild(item)

        role_tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.role_box_layout.addWidget(role_tree)

    # -------------- Utility --------------
    def _date_range(self, schedule_data):
        return sorted(schedule_data.keys(), key=lambda d: datetime.strptime(d, "%Y-%m-%d"))

    def _copy_bench_clipboard(self):
        QMessageBox.information(self, "Copy", "SHIFT x DAY table to clipboard not implemented yet.")

    def _copy_role_clipboard(self):
        QMessageBox.information(self, "Copy", "STAFF x DAY table to clipboard not implemented yet.")

    def _load_staff_order_from_manager(self):
        all_staff_objs = self.staff_manager.list_staff()
        all_inits = [s_obj.initials for s_obj in all_staff_objs]
        existing_in_self_order = [init for init in self.staff_order if init in all_inits]
        new_inits = sorted([init for init in all_inits if init not in existing_in_self_order])
        self.staff_order = existing_in_self_order + new_inits

    def _load_orders_from_file(self):
        default_staff_order = [
            "LB", "KEK", "CAM", "CML", "TL", "NM", "CMM", "GN", "DS", "JZ", "HH", "CS", "AS", "XM", "MB", "EM", "CL",
            "KL", "LH", "TG", "TS"
        ]
        default_shift_order = [
            "Cyto Nons 1", "Cyto Nons 2", "Cyto FNA", "Cyto EUS", "Cyto FLOAT", "Cyto 2ND (1)", "Cyto 2ND (2)",
            "Cyto IMG", "Cyto APERIO", "Cyto MCY", "Cyto UTD", "Cyto UTD IMG",
            "Prep AM Nons", "Prep GYN", "Prep EBUS", "Prep FNA", "Prep NONS 1", "Prep NONS 2",
            "Prep Clerical"
        ]
        if not os.path.exists(SCHEDULER_ORDER_FILE):
            return (default_staff_order, default_shift_order)
        try:
            with open(SCHEDULER_ORDER_FILE, "r") as f:
                data = json.load(f)
            staff_order = data.get("staff_order", default_staff_order)
            shift_order = data.get("shift_order", default_shift_order)
            return (staff_order, shift_order)
        except:
            return (default_staff_order, default_shift_order)

    def _save_orders_to_file(self):
        data = {"staff_order": self.staff_order, "shift_order": self.shift_order}
        os.makedirs(os.path.dirname(SCHEDULER_ORDER_FILE), exist_ok=True)
        with open(SCHEDULER_ORDER_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def _load_ebus_fridays(self):
        if not os.path.exists(EBUS_FRIDAYS_FILE):
            return []
        try:
            with open(EBUS_FRIDAYS_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except:
            return []

    def _save_ebus_fridays(self):
        os.makedirs(os.path.dirname(EBUS_FRIDAYS_FILE), exist_ok=True)
        with open(EBUS_FRIDAYS_FILE, "w") as f:
            json.dump(self.ebus_fridays, f, indent=4)
