# select_schedule_dialog.py

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QDialogButtonBox
)
from PySide6.QtCore import Qt

class SelectScheduleDialog(QDialog):
    """
    Pops up a list of saved schedule files from ReviewManager.
    User picks one, we store its info in self._chosen_info.
    """
    def __init__(self, parent, review_manager):
        super().__init__(parent)
        self.review_manager = review_manager
        self._chosen_info = None  # will hold something like {"filename": ..., "start_date":..., ...}
        self.setWindowTitle("Select Saved Schedule")

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.listwidget = QListWidget()
        layout.addWidget(self.listwidget)

        # Populate
        self._populate_list()

        btn_row = QHBoxLayout()
        layout.addLayout(btn_row)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.setStretchFactor(self.listwidget, 1)
        self.setLayout(layout)
        self.resize(400, 300)

    def _populate_list(self):
        # we assume ReviewManager has a method: list_schedules()
        # which returns list of schedule_data
        all_scheds = self.review_manager.list_schedules()
        # if you'd prefer to re-scan the folder each time, you can do so.
        for sched in all_scheds:
            # let's build display text
            st = sched.get("start_date", "????-??-??")
            ed = sched.get("end_date", "????-??-??")
            ver = sched.get("version", "unknown")
            filename = f"{st}__{ed}__{ver}.json"  # consistent with your manager
            display = f"{st} -> {ed} (v:{ver})"
            item = QListWidgetItem(display)
            # store the "info" in the item
            item.setData(Qt.UserRole, {
                "filename": filename,
                "start_date": st,
                "end_date": ed,
                "version": ver
            })
            self.listwidget.addItem(item)

    def _on_ok(self):
        item = self.listwidget.currentItem()
        if not item:
            self._chosen_info = None
        else:
            self._chosen_info = item.data(Qt.UserRole)
        self.accept()

    def get_chosen_schedule_info(self):
        return self._chosen_info
