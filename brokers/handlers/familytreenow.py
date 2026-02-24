"""
FamilyTreeNow opt-out handler.
Their opt-out form accepts name + location details directly — no profile URL needed.
"""
from brokers.handlers.base import BaseHandler


class Handler(BaseHandler):
    def submit(self) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "status": "manual_required",
                "notes": "Playwright not installed. Run: playwright install chromium. "
                         "Manual URL: https://www.familytreenow.com/optout",
            }

        if not self.full_name:
            return {"status": "manual_required", "notes": "Full name required. Check your profile."}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers({"User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )})

                page.goto("https://www.familytreenow.com/optout", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                # Fill search form
                first_input = page.query_selector("input[name='fname'], input[placeholder*='First']")
                last_input = page.query_selector("input[name='lname'], input[placeholder*='Last']")
                state_input = page.query_selector("select[name='state'], input[name='state']")

                if first_input:
                    first_input.fill(self.profile.get("first_name", ""))
                if last_input:
                    last_input.fill(self.profile.get("last_name", ""))
                if state_input and self.state:
                    tag = state_input.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "select":
                        state_input.select_option(label=self.state)
                    else:
                        state_input.fill(self.state)

                # City if available
                city_input = page.query_selector("input[name='city'], input[placeholder*='City']")
                if city_input and self.city:
                    city_input.fill(self.city)

                submit = page.query_selector("button[type='submit'], input[type='submit']")
                if submit:
                    submit.click()
                    page.wait_for_load_state("networkidle", timeout=20000)

                    # Look for record to opt out of
                    opt_buttons = page.query_selector_all("button.optout-btn, a.optout, input[value*='Opt']")
                    if opt_buttons:
                        opt_buttons[0].click()
                        page.wait_for_timeout(3000)
                        browser.close()
                        return {"status": "submitted", "notes": "Opt-out submitted on FamilyTreeNow."}

                    # If no button, we're on a results page — provide guidance
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": "Search submitted but could not click opt-out automatically. "
                                 "Visit https://www.familytreenow.com/optout to complete.",
                    }

                browser.close()
                return {
                    "status": "manual_required",
                    "notes": "Could not find form. Visit https://www.familytreenow.com/optout manually.",
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit https://www.familytreenow.com/optout manually.",
            }
