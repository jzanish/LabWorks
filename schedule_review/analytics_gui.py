# analytics_gui.py

from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCharts import (
    QChart, QChartView, QBarSet, QHorizontalBarSeries, QBarCategoryAxis, QValueAxis
)
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, QMargins


class AnalyticsWidget(QWidget):
    """
    Shows two charts side by side:
      1) The left chart is the 'Weekly Effort' bar chart
      2) The right chart is the 'Shift Count' bar chart
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        self.setLayout(layout)

        # LEFT chart view: Weekly Effort
        self.effort_chart_view = QChartView()
        self.effort_chart_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self.effort_chart_view, stretch=1)

        # RIGHT chart view: Shift Count
        self.count_chart_view = QChartView()
        self.count_chart_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self.count_chart_view, stretch=1)

    # ----------------- (A) Weekly Effort Chart (horizontal) ----------------- #
    def display_weekly_effort_bar(self, weekly_data):
        """
        weekly_data => { iso_week_number: { staff_init: effVal } }
        Creates a horizontal grouped bar chart, staff on Y-axis, one QBarSet per iso-week.
        Displayed in self.effort_chart_view (the left chart).
        """
        if not weekly_data:
            chart = QChart()
            chart.setTitle("No Weekly Data")
            self.effort_chart_view.setChart(chart)
            return

        # 1) gather staff
        all_staff = set()
        for wnum, stf_map in weekly_data.items():
            all_staff.update(stf_map.keys())
        staff_sorted = sorted(all_staff)

        # 2) build a QHorizontalBarSeries
        series = QHorizontalBarSeries()
        for wnum in sorted(weekly_data.keys()):
            stf_map = weekly_data[wnum]
            bar_set = QBarSet(f"Week {wnum}")
            for stf in staff_sorted:
                val = stf_map.get(stf, 0)
                bar_set.append(val)
            series.append(bar_set)

        chart = QChart()
        chart.setTitle("Weekly Summed Effort by Staff")
        chart.addSeries(series)

        # Y-axis => staff
        axis_y = QBarCategoryAxis()
        axis_y.setTitleText("Staff")
        axis_y.append(staff_sorted)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        # X-axis => effort points
        axis_x = QValueAxis()
        axis_x.setTitleText("Effort Points")
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        chart.setMargins(QMargins(3,3,3,3))
        self.effort_chart_view.setChart(chart)

    # -------------- (B) Shift Count Chart (horizontal) -------------- #
    def display_shift_count_bar(self, shift_count_data):
        """
        shift_count_data => { staff_init: count_of_shifts }
        Draw a single QHorizontalBarSeries in self.count_chart_view (the right chart).
        """
        if not shift_count_data:
            chart = QChart()
            chart.setTitle("No Shift Counts to Display")
            self.count_chart_view.setChart(chart)
            return

        staff_sorted = sorted(shift_count_data.keys())

        series = QHorizontalBarSeries()
        bar_set = QBarSet("Selected Shifts")
        for stf in staff_sorted:
            bar_set.append(shift_count_data[stf])
        series.append(bar_set)

        chart = QChart()
        chart.setTitle("Shift Count by Staff")
        chart.addSeries(series)

        # Y-axis => staff
        axis_y = QBarCategoryAxis()
        axis_y.setTitleText("Staff")
        axis_y.append(staff_sorted)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        # X-axis => counts
        axis_x = QValueAxis()
        axis_x.setTitleText("Count of Shifts")
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        chart.setMargins(QMargins(3,3,3,3))
        self.count_chart_view.setChart(chart)

    # -------------- (C) Clearing, if needed -------------- #
    def clear_effort_chart(self):
        chart = QChart()
        chart.setTitle("No Weekly Data")
        self.effort_chart_view.setChart(chart)

    def clear_count_chart(self):
        chart = QChart()
        chart.setTitle("No Shift Counts")
        self.count_chart_view.setChart(chart)
