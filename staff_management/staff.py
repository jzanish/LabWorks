# staff_management/staff.py

class Staff:
    def __init__(self,
                 initials: str,
                 start_time: str,
                 end_time: str,
                 role: str,
                 trained_shifts=None,
                 constraints=None,
                 is_casual=False):  # <--- add is_casual here
        """
        :param initials: Unique identifier for the staff member (e.g., "JD")
        :param start_time: e.g. "09:00"
        :param end_time: e.g. "17:00"
        :param role: e.g. "Prep Staff", "Admin", "Cytologist"
        :param trained_shifts: List of shift names
        :param constraints: Additional constraints as a dict
        :param is_casual: Boolean indicating if this staff is casual status
        """
        self.initials = initials
        self.start_time = start_time
        self.end_time = end_time
        self.role = role
        self.trained_shifts = trained_shifts or []
        self.constraints = constraints or {}
        self.is_casual = is_casual  # <--- store it

    def __repr__(self):
        return (f"Staff("
                f"initials={self.initials}, "
                f"start_time={self.start_time}, "
                f"end_time={self.end_time}, "
                f"role={self.role}, "
                f"trained_shifts={self.trained_shifts}, "
                f"constraints={self.constraints}, "
                f"is_casual={self.is_casual})")
