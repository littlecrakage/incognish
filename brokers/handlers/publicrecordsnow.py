"""
PublicRecordsNow opt-out handler.
Flow: fill opt-out form with name + city + state and submit.
Note: site may present a CAPTCHA — returns manual_required if detected.
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall

OPT_OUT_URL = "https://www.publicrecordsnow.com/static/view/optout"


class Handler(BaseHandler):
    def submit(self) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "status": "manual_required",
                "notes": f"Playwright not installed. Run: playwright install chromium. "
                         f"Manual URL: {OPT_OUT_URL}",
            }

        if not self.full_name or not self.state:
            return {
                "status": "manual_required",
                "notes": "Full name and state are required. Check your profile.",
            }

        first = self.profile.get("first_name", "")
        last = self.profile.get("last_name", "")

        try:
            with sync_playwright() as p:
                browser, page = make_stealthy_page(p)

                page.goto(OPT_OUT_URL, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                if is_bot_wall(page.title()):
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Site is protected by Cloudflare and blocks automated access. "
                                 f"Visit {OPT_OUT_URL} manually.",
                    }

                # Fill name fields
                first_input = page.query_selector(
                    "input[name='first_name'], input[name='firstname'], "
                    "input[id='first_name'], input[placeholder*='First']"
                )
                last_input = page.query_selector(
                    "input[name='last_name'], input[name='lastname'], "
                    "input[id='last_name'], input[placeholder*='Last']"
                )
                city_input = page.query_selector(
                    "input[name='city'], input[id='city'], input[placeholder*='City']"
                )
                state_input = page.query_selector(
                    "select[name='state'], input[name='state'], "
                    "select[id='state'], input[id='state']"
                )

                if first_input and first:
                    first_input.fill(first)
                if last_input and last:
                    last_input.fill(last)
                if city_input and self.city:
                    city_input.fill(self.city)
                if state_input and self.state:
                    tag = state_input.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "select":
                        try:
                            state_input.select_option(label=self.state)
                        except Exception:
                            try:
                                state_input.select_option(value=self.state[:2].upper())
                            except Exception:
                                pass
                    else:
                        state_input.fill(self.state)

                # Bail out if CAPTCHA is present
                captcha = page.query_selector(
                    "iframe[src*='recaptcha'], .g-recaptcha, iframe[src*='captcha']"
                )
                if captcha:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"CAPTCHA detected. Visit {OPT_OUT_URL} and complete the form manually.",
                    }

                submit_btn = (
                    page.query_selector("button[type='submit']")
                    or page.query_selector("input[type='submit']")
                    or page.query_selector("button:has-text('Opt')")
                    or page.query_selector("button:has-text('Submit')")
                )
                if submit_btn:
                    submit_btn.click()
                    page.wait_for_timeout(3000)
                    browser.close()
                    return {
                        "status": "submitted",
                        "notes": "Opt-out submitted to PublicRecordsNow.",
                    }

                browser.close()
                return {
                    "status": "manual_required",
                    "notes": f"Could not find form fields or submit button. Visit {OPT_OUT_URL} manually.",
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit {OPT_OUT_URL} manually.",
            }
