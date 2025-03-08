import sys
import json
import os
from datetime import datetime, date, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QComboBox, QDialog, QDialogButtonBox, QMessageBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QListWidget
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont

# If you load effort map from a JSON file, e.g.:
from scheduler.effort_map_loader import load_effort_map, DEFAULT_EFFORT

# SHIFT_COUNT_DEFAULTS:
SHIFT_COUNT_DEFAULTS = {"Cyto FNA","Cyto EUS","Cyto MCY","Cyto UTD"}

# ----------------------------------------------------------------
# SHIFT FILTER DIALOG
# ----------------------------------------------------------------
class ShiftFilterDialog(QDialog):
    def __init__(self, parent, shift_list, default_selected=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Shifts")
        self.shift_list = sorted(shift_list)

        if default_selected is None:
            # interpret None => check all
            self.default_selected = set(self.shift_list)
        else:
            self.default_selected = set(default_selected)

        self.selected_shifts = set()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        for sh_name in self.shift_list:
            cb = QCheckBox(sh_name)
            cb.setChecked(sh_name in self.default_selected)
            layout.addWidget(cb)
            setattr(self, f"checkbox_{sh_name}", cb)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_ok(self):
        for sh_name in self.shift_list:
            cb = getattr(self, f"checkbox_{sh_name}")
            if cb.isChecked():
                self.selected_shifts.add(sh_name)
        self.accept()

    def get_selected_shifts(self):
        return self.selected_shifts

# ----------------------------------------------------------------
# DUAL REORDER DIALOG
# ----------------------------------------------------------------
class DualReorderDialog(QDialog):
    """
    For reordering staff & shift lists side by side.
    """
    def __init__(self, parent, title, staff_items, shift_items, callback):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.callback = callback
        self.staff_list = list(staff_items)
        self.shift_list = list(shift_items)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        # Staff side
        staff_box = QGroupBox("Staff Order")
        top_layout.addWidget(staff_box)
        from PySide6.QtWidgets import QListWidget, QPushButton, QVBoxLayout

        s_layout = QVBoxLayout(staff_box)
        self.staff_listwidget = QListWidget()
        s_layout.addWidget(self.staff_listwidget)

        btn_col = QVBoxLayout()
        s_layout.addLayout(btn_col)
        up_s = QPushButton("Up")
        up_s.clicked.connect(self._staff_up)
        btn_col.addWidget(up_s)
        down_s = QPushButton("Down")
        down_s.clicked.connect(self._staff_down)
        btn_col.addWidget(down_s)
        btn_col.addStretch()

        # Shift side
        shift_box = QGroupBox("Shift Order")
        top_layout.addWidget(shift_box)
        sh_layout = QVBoxLayout(shift_box)
        self.shift_listwidget = QListWidget()
        sh_layout.addWidget(self.shift_listwidget)

        btn_col2 = QVBoxLayout()
        sh_layout.addLayout(btn_col2)
        up_sh = QPushButton("Up")
        up_sh.clicked.connect(self._shift_up)
        btn_col2.addWidget(up_sh)
        down_sh = QPushButton("Down")
        down_sh.clicked.connect(self._shift_down)
        btn_col2.addWidget(down_sh)
        btn_col2.addStretch()

        from PySide6.QtWidgets import QDialogButtonBox
        b_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b_box.accepted.connect(self._on_ok)
        b_box.rejected.connect(self.reject)
        main_layout.addWidget(b_box)

        self._populate()

    def _populate(self):
        self.staff_listwidget.clear()
        for s in self.staff_list:
            self.staff_listwidget.addItem(s)
        self.shift_listwidget.clear()
        for sh in self.shift_list:
            self.shift_listwidget.addItem(sh)

    def _staff_up(self):
        r = self.staff_listwidget.currentRow()
        if r<=0:
            return
        self.staff_list[r], self.staff_list[r-1] = self.staff_list[r-1], self.staff_list[r]
        self._populate()
        self.staff_listwidget.setCurrentRow(r-1)

    def _staff_down(self):
        r = self.staff_listwidget.currentRow()
        if r<0 or r>= len(self.staff_list)-1:
            return
        self.staff_list[r], self.staff_list[r+1] = self.staff_list[r+1], self.staff_list[r]
        self._populate()
        self.staff_listwidget.setCurrentRow(r+1)

    def _shift_up(self):
        r = self.shift_listwidget.currentRow()
        if r<=0:
            return
        self.shift_list[r], self.shift_list[r-1] = self.shift_list[r-1], self.shift_list[r]
        self._populate()
        self.shift_listwidget.setCurrentRow(r-1)

    def _shift_down(self):
        r = self.shift_listwidget.currentRow()
        if r<0 or r>= len(self.shift_list)-1:
            return
        self.shift_list[r], self.shift_list[r+1] = self.shift_list[r+1], self.shift_list[r]
        self._populate()
        self.shift_listwidget.setCurrentRow(r+1)

    def _on_ok(self):
        self.callback(self.staff_list, self.shift_list)
        self.accept()

# ----------------------------------------------------------------
# MANUAL ASSIGNMENT DIALOG
# ----------------------------------------------------------------
class ManualAssignmentDialog(QDialog):
    def __init__(
        self, parent, title,
        day_list, shift_list, staff_list, callback,
        existing_preassigned=None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.callback = callback
        self.day_list = day_list
        self.shift_list = shift_list
        self.staff_list = staff_list
        self.existing_preassigned = existing_preassigned or {}
        self.cell_widgets = {}
        self._build_ui()
        self._populate_existing()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        top_frame = QWidget()
        layout.addWidget(top_frame)

        from PySide6.QtWidgets import QGridLayout, QLabel, QComboBox, QDialogButtonBox
        g_layout = QGridLayout(top_frame)

        corner_lbl = QLabel("Shift \\ Day")
        g_layout.addWidget(corner_lbl, 0, 0)

        import datetime as dt
        for col_idx, d_str in enumerate(self.day_list):
            d_obj = dt.datetime.strptime(d_str, "%Y-%m-%d")
            heading = d_obj.strftime("%a %m/%d")
            hlbl = QLabel(heading)
            hlbl.setAlignment(Qt.AlignCenter)
            g_layout.addWidget(hlbl, 0, col_idx+1)

        for s_idx, sh_name in enumerate(self.shift_list):
            row_idx = s_idx + 1
            lab = QLabel(sh_name)
            g_layout.addWidget(lab, row_idx, 0)

            for col_idx, d_str in enumerate(self.day_list):
                combo = QComboBox()
                combo.addItem("None")
                for stf_init in self.staff_list:
                    combo.addItem(stf_init)
                g_layout.addWidget(combo, row_idx, col_idx+1)
                self.cell_widgets[(d_str, sh_name)] = combo

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # stretch
        cols = len(self.day_list)+1
        for c in range(cols):
            g_layout.setColumnStretch(c,1)

    def _populate_existing(self):
        for (d_str, sh_name), stf_init in self.existing_preassigned.items():
            combo = self.cell_widgets.get((d_str, sh_name))
            if combo:
                # ensure stf_init is in combo
                idx = None
                for i in range(combo.count()):
                    if combo.itemText(i)==stf_init:
                        idx = i
                        break
                if idx is not None:
                    combo.setCurrentIndex(idx)
                else:
                    combo.addItem(stf_init)
                    combo.setCurrentText(stf_init)

    def _on_ok(self):
        res = {}
        for (d_str, sh_name), combo in self.cell_widgets.items():
            chosen = combo.currentText()
            if chosen and chosen!="None":
                res[(d_str, sh_name)] = chosen
        self.callback(res)
        self.accept()

# ----------------------------------------------------------------
# EBUS FRIDAY DIALOG
# ----------------------------------------------------------------
class EbusFridayDialog(QDialog):
    def __init__(self, parent, ebus_list, callback_save):
        super().__init__(parent)
        self.setWindowTitle("Manage EBUS Fridays")
        self.callback_save = callback_save
        self.ebus_dates = set(ebus_list)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        lbl = QLabel("EBUS Fridays (YYYY-MM-DD):")
        layout.addWidget(lbl)

        from PySide6.QtWidgets import QListWidget, QLineEdit, QPushButton, QDialogButtonBox, QHBoxLayout
        self.listwidget = QListWidget()
        layout.addWidget(self.listwidget)

        hl = QHBoxLayout()
        layout.addLayout(hl)
        self.new_date_edit = QLineEdit()
        self.new_date_edit.setPlaceholderText("YYYY-MM-DD")
        hl.addWidget(self.new_date_edit)

        add_b = QPushButton("Add")
        add_b.clicked.connect(self._on_add)
        hl.addWidget(add_b)

        rm_b = QPushButton("Remove Selected")
        rm_b.clicked.connect(self._on_remove)
        layout.addWidget(rm_b)

        bb = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _populate(self):
        self.listwidget.clear()
        for d_str in sorted(self.ebus_dates):
            self.listwidget.addItem(d_str)

    def _on_add(self):
        from datetime import datetime
        d_str = self.new_date_edit.text().strip()
        if not d_str:
            return
        try:
            dt_obj = datetime.strptime(d_str,"%Y-%m-%d")
        except ValueError:
            QMessageBox.critical(self, "Invalid Date","Must be YYYY-MM-DD.")
            return
        # check friday
        if dt_obj.weekday()!=4:
            r = QMessageBox.question(self, "Not Friday","Date not Friday, proceed?")
            if r!=QMessageBox.Yes:
                return
        if d_str not in self.ebus_dates:
            self.ebus_dates.add(d_str)
            self._populate()
        self.new_date_edit.clear()

    def _on_remove(self):
        item = self.listwidget.currentItem()
        if item:
            self.ebus_dates.discard(item.text())
            self._populate()

    def _on_ok(self):
        self.callback_save(sorted(self.ebus_dates))
        self.accept()


# ----------------------------------------------------------------
# Suppose you have the Analytics code in schedule_review.analytics,
# and an AnalyticsWidget in schedule_review.analytics_gui
# We do an import here:
from schedule_review.analytics import ScheduleAnalytics
from schedule_review.analytics_gui import AnalyticsWidget

# SHIFT_COUNT_DEFAULTS we defined above:
# SHIFT_COUNT_DEFAULTS = {"Cyto FNA","Cyto EUS","Cyto MCY","Cyto UTD"}

# ----------------------------------------------------------------
# The SCHEDULER TAB
# ----------------------------------------------------------------
class SchedulerTab(QWidget):
    def __init__(self, parent,
                 ortools_scheduler,
                 staff_manager,
                 shift_manager,
                 review_manager=None,
                 availability_manager=None):
        super().__init__(parent)

        self.ortools_scheduler = ortools_scheduler
        self.staff_manager = staff_manager
        self.shift_manager = shift_manager
        self.review_manager = review_manager
        self.availability_manager = availability_manager

        self.last_generated_schedule = None
        self.role_order = ["Cytologist","Admin","Prep Staff","Unscheduled"]
        self._preassigned = {}
        self.staff_order, self.shift_order = self._load_orders_from_file()
        self.ebus_fridays = self._load_ebus_fridays()

        # We'll store “which shifts for weekly effort” or for shift count if you want.
        # But for auto display we’ll just pass None or SHIFT_COUNT_DEFAULTS.
        self.included_shifts_effort = None
        self.included_shifts_counts = None

        self._build_ui()
        self._load_staff_order_from_manager()

    def _build_ui(self):
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        left_side = QVBoxLayout()
        main_layout.addLayout(left_side, stretch=3)

        self.bench_box = QGroupBox("Shift-Based Assignments")
        left_side.addWidget(self.bench_box)
        self.bench_layout = QVBoxLayout(self.bench_box)

        self.role_box = QGroupBox("Role-Based Schedule")
        left_side.addWidget(self.role_box)
        self.role_layout = QVBoxLayout(self.role_box)

        # row for date pickers, generate
        row_inp = QHBoxLayout()
        left_side.addLayout(row_inp)
        self._create_input_ui(row_inp)

        # row for reorder/manual/ebus + filter
        row_btn = QHBoxLayout()
        left_side.addLayout(row_btn)
        self._create_reorder_button(row_btn)
        self._create_manual_assign_button(row_btn)
        self._create_ebus_button(row_btn)

        # SHIFT filter (weekly effort)
        filter_eff_btn = QPushButton("Filter Shifts (Weekly Effort)")
        filter_eff_btn.clicked.connect(self._on_filter_shifts_effort)
        row_btn.addWidget(filter_eff_btn)

        # SHIFT count
        shift_count_btn = QPushButton("Show SHIFT Counts")
        shift_count_btn.clicked.connect(self._on_show_shift_counts)
        row_btn.addWidget(shift_count_btn)

        row_btn.addStretch(1)

        # right side => analytics
        self.analytics_view = AnalyticsWidget(self)
        main_layout.addWidget(self.analytics_view, stretch=2)

    # -------------- SHIFT filter logic + SHIFT counts --------------
    def _on_filter_shifts_effort(self):
        if not self.last_generated_schedule:
            QMessageBox.warning(self, "No Schedule","Generate schedule first.")
            return
        shift_list = self._gather_shifts_from_sched(self.last_generated_schedule)
        if not shift_list:
            QMessageBox.information(self,"No Shifts","No shifts in schedule.")
            return

        dlg = ShiftFilterDialog(self, shift_list, default_selected=None)  # check all by default
        if dlg.exec()==QDialog.Accepted:
            self.included_shifts_effort = dlg.get_selected_shifts()
            analyzer = ScheduleAnalytics()
            weekly_data = analyzer.calc_weekly_effort(
                {"assignments": self.last_generated_schedule},
                included_shifts=self.included_shifts_effort
            )
            self.analytics_view.display_weekly_effort_bar(weekly_data)

    def _on_show_shift_counts(self):
        if not self.last_generated_schedule:
            QMessageBox.warning(self,"No Schedule","Generate schedule first.")
            return
        shift_list = self._gather_shifts_from_sched(self.last_generated_schedule)
        if not shift_list:
            QMessageBox.information(self,"No Shifts","No shifts in schedule.")
            return

        dlg = ShiftFilterDialog(self, shift_list, default_selected=SHIFT_COUNT_DEFAULTS)
        if dlg.exec()==QDialog.Accepted:
            self.included_shifts_counts = dlg.get_selected_shifts()
            analyzer = ScheduleAnalytics()
            shift_counts = analyzer.calc_shift_counts(
                {"assignments": self.last_generated_schedule},
                included_shifts=self.included_shifts_counts
            )
            self.analytics_view.display_shift_count_bar(shift_counts)

    def _gather_shifts_from_sched(self, sched):
        sset = set()
        for day_str, recs in sched.items():
            for r in recs:
                sset.add(r.get("shift",""))
        return sorted(sset)

    # -------------- input UI, reorder, manual, EBUS --------------
    def _create_input_ui(self, layout):
        layout.addWidget(QLabel("Start Date:"))
        self.start_dateedit = QDateEdit()
        self.start_dateedit.setDate(QDate(2025,1,6))
        self.start_dateedit.setCalendarPopup(True)
        self.start_dateedit.dateChanged.connect(self._auto_set_end_date)
        layout.addWidget(self.start_dateedit)

        layout.addWidget(QLabel("End Date:"))
        self.end_dateedit = QDateEdit()
        self.end_dateedit.setDate(QDate(2025,1,10))
        self.end_dateedit.setCalendarPopup(True)
        layout.addWidget(self.end_dateedit)

        gen_btn = QPushButton("Generate Schedule")
        gen_btn.clicked.connect(self.generate_schedule)
        layout.addWidget(gen_btn)

        rev_btn = QPushButton("Send to Schedule Review →")
        rev_btn.clicked.connect(self._on_send_to_review)
        layout.addWidget(rev_btn)

        layout.addStretch(1)

    def _auto_set_end_date(self, qdate):
        dt_s = date(qdate.year(), qdate.month(), qdate.day())
        offset = (4 - dt_s.weekday())%7
        dt_e = dt_s + timedelta(days=offset)
        self.end_dateedit.setDate(QDate(dt_e.year, dt_e.month, dt_e.day))

    def _create_reorder_button(self, layout):
        b = QPushButton("Reorder Staff & Shifts")
        b.clicked.connect(self._open_reorder_dialog)
        layout.addWidget(b)

    def _open_reorder_dialog(self):
        def reorder_cb(new_staff, new_shifts):
            self.staff_order = new_staff
            self.shift_order = new_shifts
            self._save_orders_to_file()
            QMessageBox.information(self,"Order Updated","Staff & shift order updated.")
            self._refresh_schedule_display()

        d = DualReorderDialog(self,"Reorder Staff & Shifts",
                              self.staff_order,
                              self.shift_order,
                              reorder_cb)
        d.exec()

    def _create_manual_assign_button(self, layout):
        b = QPushButton("Manual Assignments")
        b.clicked.connect(self._open_manual_dialog)
        layout.addWidget(b)

    def _open_manual_dialog(self):
        dt_s = date(self.start_dateedit.date().year(),
                    self.start_dateedit.date().month(),
                    self.start_dateedit.date().day())
        dt_e = date(self.end_dateedit.date().year(),
                    self.end_dateedit.date().month(),
                    self.end_dateedit.date().day())
        if dt_e<dt_s:
            QMessageBox.critical(self,"Invalid Date","End date < start date.")
            return

        day_list = []
        cur = dt_s
        while cur<=dt_e:
            if cur.weekday()<5:
                day_list.append(cur.strftime("%Y-%m-%d"))
            cur+= timedelta(days=1)

        all_shifts = self.shift_manager.list_shifts()
        sh_map = {sh.name:sh for sh in all_shifts}
        sh_ordered = [x for x in self.shift_order if x in sh_map]
        leftover = [x for x in sh_map if x not in sh_ordered]
        final_sh = sh_ordered + leftover

        st_objs = self.staff_manager.list_staff()
        st_inits = [so.initials for so in st_objs]

        def on_ok(pdict):
            self._preassigned.update(pdict)
            QMessageBox.information(self,"Manual Assignments","Assignments updated in memory.")
            self.generate_schedule()

        d = ManualAssignmentDialog(
            self,"Manual Assignments",
            day_list, final_sh, st_inits, on_ok,
            existing_preassigned=self._preassigned
        )
        d.exec()

    def _create_ebus_button(self, layout):
        b = QPushButton("Manage EBUS Fridays")
        b.clicked.connect(self._open_ebus_dialog)
        layout.addWidget(b)

    def _open_ebus_dialog(self):
        def saver(new_dates):
            self.ebus_fridays = new_dates
            self._save_ebus_fridays()
            QMessageBox.information(self,"EBUS Fridays Updated","Saved new EBUS list.")
        d = EbusFridayDialog(self, self.ebus_fridays, saver)
        d.exec()

    # -------------- Generate Schedule => also auto-display 2 charts --------------
    def generate_schedule(self):
        self._load_staff_order_from_manager()

        dt_s = date(self.start_dateedit.date().year(),
                    self.start_dateedit.date().month(),
                    self.start_dateedit.date().day())
        dt_e = date(self.end_dateedit.date().year(),
                    self.end_dateedit.date().month(),
                    self.end_dateedit.date().day())
        if dt_e<dt_s:
            QMessageBox.critical(self,"Invalid Date","End date < start date.")
            return

        s_str = dt_s.strftime("%Y-%m-%d")
        e_str = dt_e.strftime("%Y-%m-%d")

        # check EBUS
        is_ebus_in_range = False
        c = dt_s
        while c<=dt_e:
            if c.weekday()==4:
                if c.strftime("%Y-%m-%d") in self.ebus_fridays:
                    is_ebus_in_range = True
                    break
            c+= timedelta(days=1)

        sched_data = self.ortools_scheduler.generate_schedule(
            s_str,e_str,
            preassigned=self._preassigned,
            is_ebus_friday=is_ebus_in_range
        )
        if not sched_data:
            QMessageBox.information(self,"No Schedule","No feasible solution or empty.")
            return

        self.last_generated_schedule = sched_data

        # clear old SHIFT/ROLE
        for i in reversed(range(self.bench_layout.count())):
            w = self.bench_layout.itemAt(i).widget()
            if w: w.deleteLater()
        for i in reversed(range(self.role_layout.count())):
            w = self.role_layout.itemAt(i).widget()
            if w: w.deleteLater()

        self._build_bench_table(sched_data)
        self._build_role_table(sched_data)

        QMessageBox.information(self,"Schedule Generated","Schedule generated successfully!")

        # NOW auto-display the charts
        self._auto_display_charts()

    def _auto_display_charts(self):
        """
        After schedule is generated, automatically display:
          1) Weekly Effort (all shifts)
          2) SHIFT Count (with SHIFT_COUNT_DEFAULTS)
        """
        if not self.last_generated_schedule:
            return

        # 1) Weekly Effort (all shifts => included_shifts=None)
        analyzer = ScheduleAnalytics()
        weekly_data = analyzer.calc_weekly_effort(
            {"assignments": self.last_generated_schedule},
            included_shifts=None   # i.e. sum all
        )
        self.analytics_view.display_weekly_effort_bar(weekly_data)

        # 2) SHIFT Count (with SHIFT_COUNT_DEFAULTS)
        shift_counts = analyzer.calc_shift_counts(
            {"assignments": self.last_generated_schedule},
            included_shifts=SHIFT_COUNT_DEFAULTS
        )
        # We'll call the method that draws shift-count bar:
        self.analytics_view.display_shift_count_bar(shift_counts)


    def _on_send_to_review(self):
        if not self.last_generated_schedule:
            QMessageBox.warning(self,"No Schedule","Generate a schedule first.")
            return
        dt_s = date(self.start_dateedit.date().year(),
                    self.start_dateedit.date().month(),
                    self.start_dateedit.date().day())
        dt_e = date(self.end_dateedit.date().year(),
                    self.end_dateedit.date().month(),
                    self.end_dateedit.date().day())
        s_str = dt_s.strftime("%Y-%m-%d")
        e_str = dt_e.strftime("%Y-%m-%d")

        payload = {
            "start_date": s_str,
            "end_date": e_str,
            "assignments": self.last_generated_schedule,
            "created_at": datetime.now().isoformat()
        }
        if self.review_manager:
            self.review_manager.commit_schedule(payload)
            QMessageBox.information(
                self,"Schedule Review",
                f"Schedule sent to review for {s_str}→{e_str}."
            )
        else:
            QMessageBox.critical(self,"No Review Manager","No review_manager attached to SchedulerTab!")


    # -------------- SHIFT-based Table --------------
    def _build_bench_table(self, schedule_data):
        day_list = sorted(schedule_data.keys(), key=lambda d: datetime.strptime(d, "%Y-%m-%d"))
        def friendly_date(d_str):
            return datetime.strptime(d_str,"%Y-%m-%d").strftime("%a %-m/%-d")
        headers = [friendly_date(d) for d in day_list]

        # shift map
        shift_map = {}
        for d_str, recs in schedule_data.items():
            for rec in recs:
                sh = rec["shift"]
                who = rec["assigned_to"]
                shift_map.setdefault(sh, {})[d_str] = who

        in_sched = list(shift_map.keys())
        sh_ordered = [x for x in self.shift_order if x in in_sched]
        leftover = [x for x in in_sched if x not in sh_ordered]
        sh_ordered += leftover

        row_count = len(sh_ordered)
        col_count = len(day_list)
        table = QTableWidget(row_count, col_count)
        table.setHorizontalHeaderLabels(headers)
        table.setVerticalHeaderLabels(sh_ordered)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setFont(QFont(table.font().family(), table.font().pointSize() - 2))

        def get_shift_obj(sh_name):
            for s in self.shift_manager.list_shifts():
                if s.name == sh_name:
                    return s
            return None

        for r, sh_name in enumerate(sh_ordered):
            day_dict = shift_map[sh_name]
            sh_obj = get_shift_obj(sh_name)
            for c, d_str in enumerate(day_list):
                st_init = day_dict.get(d_str,"")
                if st_init=="Unassigned":
                    st_init="OPEN"
                item = QTableWidgetItem(st_init)
                if st_init=="OPEN" and sh_obj and getattr(sh_obj,"can_remain_open",False):
                    item.setBackground(QColor("yellow"))
                    item.setForeground(QColor("black"))
                table.setItem(r,c,item)

        self.bench_layout.addWidget(table)

    # -------------- ROLE-based Table --------------
    def _build_role_table(self, schedule_data):
        day_list = sorted(schedule_data.keys(), key=lambda d: datetime.strptime(d, "%Y-%m-%d"))
        def friendly_date(d_str):
            return datetime.strptime(d_str,"%Y-%m-%d").strftime("%a %-m/%-d")
        headers = [friendly_date(x) for x in day_list]

        # staff->role
        stf_role = {}
        for s_obj in self.staff_manager.list_staff():
            if s_obj.role in ["Cytologist","Admin","Prep Staff"]:
                stf_role[s_obj.initials] = s_obj.role
            else:
                stf_role[s_obj.initials] = "Unscheduled"

        # role_map => role -> { init -> {day->shift} }
        role_map = {}
        for d_str, recs in schedule_data.items():
            for rec in recs:
                st_init = rec["assigned_to"]
                if st_init=="Unassigned":
                    continue
                shift_nm = rec["shift"]
                assigned_role = rec.get("role","") or stf_role.get(st_init,"Unscheduled")
                role_map.setdefault(assigned_role,{}).setdefault(st_init,{})[d_str] = shift_nm

        # ensure all staff
        for st_init, ro in stf_role.items():
            role_map.setdefault(ro,{}).setdefault(st_init,{})

        # reorder roles
        roles_in_sched = list(role_map.keys())
        role_ordered = ["Cytologist","Admin","Prep Staff","Unscheduled"]
        leftover = [r for r in roles_in_sched if r not in role_ordered]
        for rr in leftover:
            role_ordered.append(rr)

        # flatten
        row_entries = []
        for ro_name in role_ordered:
            if ro_name not in role_map:
                continue
            st_map = role_map[ro_name]
            staff_in_role = sorted(st_map.keys())
            for st_init in staff_in_role:
                row_entries.append((ro_name, st_init))

        row_count = len(row_entries)
        col_count = len(day_list)
        table = QTableWidget(row_count, col_count)
        table.setHorizontalHeaderLabels(headers)

        vert_labels = []
        for (rname, sinit) in row_entries:
            vert_labels.append(f"{rname} - {sinit}")
        table.setVerticalHeaderLabels(vert_labels)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setFont(QFont(table.font().family(), table.font().pointSize() - 2))

        def get_avail_reason(st_init,d_str):
            if not self.availability_manager:
                return ""
            for rec in self.availability_manager.list_availability():
                if rec["initials"]==st_init and rec["date"]==d_str:
                    return rec.get("reason","")
            return ""

        def is_holiday(d_str):
            if not self.availability_manager:
                return False
            return self.availability_manager.is_holiday(d_str)

        for r_i, (ro_name, st_init) in enumerate(row_entries):
            st_day_map = role_map[ro_name][st_init]
            for c_i, d_str in enumerate(day_list):
                sh_asg = st_day_map.get(d_str,"")
                if sh_asg=="Unassigned":
                    sh_asg=""
                reason = get_avail_reason(st_init,d_str)

                if reason:
                    if sh_asg:
                        text = f"{sh_asg} ({reason})"
                    else:
                        text = reason
                else:
                    text = sh_asg

                item = QTableWidgetItem(text)

                if is_holiday(d_str):
                    item.setBackground(QColor("teal"))
                else:
                    if reason=="PTO":
                        item.setBackground(QColor("green"))
                    elif reason in ("0.5 FTE","0.8 FTE"):
                        item.setBackground(QColor("blue"))
                    elif reason=="SSL":
                        item.setBackground(QColor("red"))
                    elif reason:
                        item.setBackground(QColor("yellow"))
                table.setItem(r_i,c_i,item)

        self.role_layout.addWidget(table)

    # -------------- UTILITY --------------
    def _refresh_schedule_display(self):
        self.generate_schedule()

    def _load_staff_order_from_manager(self):
        all_st = self.staff_manager.list_staff()
        all_inits = [x.initials for x in all_st]
        exist = [xx for xx in self.staff_order if xx in all_inits]
        new_ones = sorted(set(all_inits)-set(exist))
        self.staff_order = exist+new_ones

    def _load_orders_from_file(self):
        SCHEDULER_ORDER_FILE = "data/scheduler_order.json"
        def_staff = [
            "LB","KEK","CAM","CML","TL","NM","CMM","GN","DS","JZ","HH",
            "CS","AS","XM","MB","EM","CL","KL","LH","TG","TS"
        ]
        def_shift = [
            "Cyto Nons 1","Cyto Nons 2","Cyto FNA","Cyto EUS","Cyto FLOAT",
            "Cyto 2ND (1)","Cyto 2ND (2)","Cyto IMG","Cyto APERIO","Cyto MCY",
            "Cyto UTD","Cyto UTD IMG","Prep AM Nons","Prep GYN","Prep EBUS",
            "Prep FNA","Prep NONS 1","Prep NONS 2","Prep Clerical"
        ]
        if not os.path.exists(SCHEDULER_ORDER_FILE):
            return (def_staff, def_shift)
        try:
            with open(SCHEDULER_ORDER_FILE,"r") as f:
                data = json.load(f)
            so = data.get("staff_order", def_staff)
            sho = data.get("shift_order", def_shift)
            return (so,sho)
        except:
            return (def_staff,def_shift)

    def _save_orders_to_file(self):
        SCHEDULER_ORDER_FILE = "data/scheduler_order.json"
        data = {
            "staff_order": self.staff_order,
            "shift_order": self.shift_order
        }
        os.makedirs(os.path.dirname(SCHEDULER_ORDER_FILE), exist_ok=True)
        with open(SCHEDULER_ORDER_FILE,"w") as f:
            json.dump(data,f,indent=4)

    def _load_ebus_fridays(self):
        EBUS_FRIDAYS_FILE = "data/ebus_fridays.json"
        if not os.path.exists(EBUS_FRIDAYS_FILE):
            return []
        try:
            with open(EBUS_FRIDAYS_FILE,"r") as f:
                data = json.load(f)
            if isinstance(data,list):
                return data
            return []
        except:
            return []

    def _save_ebus_fridays(self):
        EBUS_FRIDAYS_FILE = "data/ebus_fridays.json"
        os.makedirs(os.path.dirname(EBUS_FRIDAYS_FILE), exist_ok=True)
        with open(EBUS_FRIDAYS_FILE,"w") as f:
            json.dump(self.ebus_fridays,f,indent=4)
