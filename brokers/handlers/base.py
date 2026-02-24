"""Base class for all broker handlers."""


class BaseHandler:
    def __init__(self, profile: dict, broker: dict):
        self.profile = profile
        self.broker = broker

    def submit(self) -> dict:
        """
        Submit opt-out request.
        Returns: {"status": str, "notes": str}
        status values: submitted | confirmed | error | manual_required
        """
        raise NotImplementedError

    # ── Helpers ────────────────────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        first = self.profile.get("first_name", "")
        last = self.profile.get("last_name", "")
        return f"{first} {last}".strip() or self.profile.get("full_name", "")

    @property
    def email(self) -> str:
        return self.profile.get("email", "")

    @property
    def phone(self) -> str:
        return self.profile.get("phone", "")

    @property
    def city(self) -> str:
        return self.profile.get("city", "")

    @property
    def state(self) -> str:
        return self.profile.get("state", "")

    @property
    def address(self) -> str:
        return self.profile.get("address", "")

    @property
    def zip_code(self) -> str:
        return self.profile.get("zip_code", "")

    @property
    def dob(self) -> str:
        return self.profile.get("date_of_birth", "")
