# shift_management/shift.py

class Shift:
    def __init__(self,
                 name,
                 role_required="Any",
                 is_flexible=False,
                 can_remain_open=False,
                 start_time=None,
                 end_time=None,
                 days_of_week=None):
        """
        :param name: The shift name (e.g. "Bench A", "Morning Shift").
        :param role_required: "Any" or a specific role needed.
        :param is_flexible: If True, shift hours can adapt.
        :param can_remain_open: If True, shift can remain unfilled.
        :param start_time: e.g. "08:00"
        :param end_time: e.g. "16:00"
        :param days_of_week: List of days for which this shift is needed
                             (e.g., ["Monday", "Tuesday"]).
        """
        self.name = name
        self.role_required = role_required
        self.is_flexible = is_flexible
        self.can_remain_open = can_remain_open
        self.start_time = start_time
        self.end_time = end_time
        self.days_of_week = days_of_week or []  # e.g., ["Monday", "Tuesday"]

    def __repr__(self):
        return (f"Shift(name={self.name}, role_required={self.role_required}, "
                f"is_flexible={self.is_flexible}, can_remain_open={self.can_remain_open}, "
                f"start_time={self.start_time}, end_time={self.end_time}, "
                f"days_of_week={self.days_of_week})")
