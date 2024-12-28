# availability_management/availability.py

class AvailabilityRecord:
    def __init__(self, initials, date, reason="PTO"):
        """
        :param initials: Staff member's initials
        :param date: YYYY-MM-DD string
        :param reason: "PTO", "Sick", etc.
        """
        self.initials = initials
        self.date = date
        self.reason = reason

    def __repr__(self):
        return f"AvailabilityRecord({self.initials}, {self.date}, reason={self.reason})"
