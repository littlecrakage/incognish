"""
PeopleFinders opt-out handler.
Flow: navigate to opt-out page → solve Turnstile → fill form → submit.
Email confirmation required to finalize removal.
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall
from brokers.handlers.capsolver_helper import (
    extract_turnstile_sitekey, solve_turnstile, inject_turnstile_token,
)

OPT_OUT_URL = "https://www.peoplefinders.com/manage"


class Handler(BaseHandler):
    def submit(self) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "status": "manual_required",
                "notes": f"Playwright not installed. Run: playwright install chromium. Manual URL: {OPT_OUT_URL}",
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
                        "notes": f"Site blocked automated access. Visit {OPT_OUT_URL} manually.",
                    }

                # Solve Turnstile if present
                turnstile = page.query_selector("[data-sitekey], iframe[src*='challenges.cloudflare']")
                if turnstile:
                    site_key = extract_turnstile_sitekey(page)
                    token = solve_turnstile(OPT_OUT_URL, site_key) if site_key else None
                    if not token:
                        browser.close()
                        return {
                            "status": "manual_required",
                            "notes": f"Turnstile could not be solved. Visit {OPT_OUT_URL} manually.",
                        }
                    inject_turnstile_token(page, token)
                    page.wait_for_timeout(2000)

                # Fill search form
                first_el = page.query_selector("input[name='firstName'], input[placeholder*='First'], input[name='fn']")
                last_el  = page.query_selector("input[name='lastName'],  input[placeholder*='Last'],  input[name='ln']")
                state_el = page.query_selector("select[name='state'], input[name='state']")
                email_el = page.query_selector("input[type='email'], input[name='email']")

                if first_el and first:
                    first_el.fill(first)
                if last_el and last:
                    last_el.fill(last)
                if state_el and self.state:
                    tag = state_el.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "select":
                        try:
                            state_el.select_option(label=self.state)
                        except Exception:
                            state_el.select_option(value=self.state[:2].upper())
                    else:
                        state_el.fill(self.state)
                if email_el and self.email:
                    email_el.fill(self.email)

                submit = page.query_selector("button[type='submit'], input[type='submit']")
                if submit:
                    submit.click()
                    page.wait_for_load_state("networkidle", timeout=20000)

                    # Click opt-out on result if shown
                    opt_btn = (
                        page.query_selector("a:has-text('Opt Out')")
                        or page.query_selector("button:has-text('Remove')")
                    )
                    if opt_btn:
                        opt_btn.click()
                        page.wait_for_timeout(3000)

                    browser.close()
                    return {
                        "status": "submitted",
                        "notes": (
                            "Opt-out submitted to PeopleFinders. "
                            "Check your email and click the confirmation link to complete removal."
                        ),
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
