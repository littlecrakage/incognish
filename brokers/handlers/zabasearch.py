"""
ZabaSearch opt-out handler.
Note: ZabaSearch is owned by PeopleConnect (same as Intelius/TruthFinder).
Opt-out goes through the PeopleConnect Suppression Center.
Flow: navigate to suppression center → solve Turnstile → submit email → verify.
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall
from brokers.handlers.capsolver_helper import (
    extract_turnstile_sitekey, solve_turnstile, inject_turnstile_token,
)

OPT_OUT_URL = "https://suppression.peopleconnect.us/login"


class Handler(BaseHandler):
    def submit(self) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "status": "manual_required",
                "notes": f"Playwright not installed. Run: playwright install chromium. Manual URL: {OPT_OUT_URL}",
            }

        if not self.email:
            return {
                "status": "manual_required",
                "notes": "Email is required. Check your profile.",
            }

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

                # Fill email on the suppression center login/start form
                email_el = page.query_selector("input[type='email'], input[name='email']")
                if email_el:
                    email_el.fill(self.email)

                # Accept terms if checkbox is present
                terms = page.query_selector("input[type='checkbox']")
                if terms:
                    terms.check()

                submit = page.query_selector("button[type='submit'], input[type='submit']")
                if submit:
                    submit.click()
                    page.wait_for_timeout(3000)
                    browser.close()
                    return {
                        "status": "submitted",
                        "notes": (
                            "Suppression request initiated at PeopleConnect (covers ZabaSearch, "
                            "Intelius, TruthFinder, InstantCheckmate). "
                            "Check your email and complete identity verification to finalize."
                        ),
                    }

                browser.close()
                return {
                    "status": "manual_required",
                    "notes": f"Could not submit form. Visit {OPT_OUT_URL} manually.",
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit {OPT_OUT_URL} manually.",
            }
