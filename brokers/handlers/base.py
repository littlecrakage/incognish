"""Base class for all broker handlers."""


def make_stealthy_page(playwright):
    """
    Launch a stealthy browser page using real Chrome + playwright-stealth.
    Falls back to plain Chromium if Chrome or playwright-stealth is unavailable.
    Returns (browser, page).
    """
    args = ["--disable-blink-features=AutomationControlled"]

    try:
        from playwright_stealth import Stealth
        stealth = Stealth()
    except ImportError:
        stealth = None

    # Prefer real Chrome; fall back to bundled Chromium
    try:
        browser = playwright.chromium.launch(channel="chrome", headless=True, args=args)
    except Exception:
        browser = playwright.chromium.launch(headless=True, args=args)

    page = browser.new_page(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )

    if stealth:
        stealth.apply_stealth_sync(page)

    return browser, page


def is_bot_wall(title: str) -> bool:
    """Return True if the page title indicates a Cloudflare or bot-detection wall."""
    markers = ["Attention Required", "Just a moment", "Challenge", "Access Denied",
               "403 Forbidden", "SSL handshake"]
    return any(m in title for m in markers)


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
