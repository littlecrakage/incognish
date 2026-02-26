"""
FamilyTreeNow opt-out handler.
Their opt-out form accepts name + location details directly — no profile URL needed.
Uses stealthy browser to bypass bot detection.
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall

OPT_OUT_URL = "https://www.familytreenow.com/optout"


class Handler(BaseHandler):
    def submit(self) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "status": "manual_required",
                "notes": f"Playwright not installed. Run: playwright install chromium. Manual URL: {OPT_OUT_URL}",
            }

        if not self.full_name:
            return {"status": "manual_required", "notes": "Full name required. Check your profile."}

        try:
            with sync_playwright() as p:
                browser, page = make_stealthy_page(p)

                page.goto(OPT_OUT_URL, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                if is_bot_wall(page.title()):
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Site blocked automated access (Cloudflare). Visit {OPT_OUT_URL} manually.",
                    }

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

                city_input = page.query_selector("input[name='city'], input[placeholder*='City']")
                if city_input and self.city:
                    city_input.fill(self.city)

                submit = page.query_selector("button[type='submit'], input[type='submit']")
                if submit:
                    submit.click()
                    page.wait_for_load_state("networkidle", timeout=20000)

                    opt_buttons = page.query_selector_all(
                        "button.optout-btn, a.optout, input[value*='Opt']"
                    )
                    if opt_buttons:
                        opt_buttons[0].click()
                        page.wait_for_timeout(3000)
                        browser.close()
                        return {"status": "submitted", "notes": "Opt-out submitted on FamilyTreeNow."}

                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Search submitted but could not click opt-out automatically. Visit {OPT_OUT_URL} to complete.",
                    }

                browser.close()
                return {
                    "status": "manual_required",
                    "notes": f"Could not find form. Visit {OPT_OUT_URL} manually.",
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit {OPT_OUT_URL} manually.",
            }
