"""
ThatsThem opt-out handler.
Flow: fill the opt-out form → solve reCAPTCHA v2 via CapSolver (if configured) → submit.
Falls back to manual_required if CAPTCHA cannot be solved automatically.
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall
from brokers.handlers.capsolver_helper import (
    extract_recaptcha_sitekey, solve_recaptcha_v2, inject_recaptcha_token,
)

OPT_OUT_URL = "https://thatsthem.com/optout"


class Handler(BaseHandler):
    def submit(self) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "status": "manual_required",
                "notes": f"Playwright not installed. Run: playwright install chromium. Manual URL: {OPT_OUT_URL}",
            }

        if not self.full_name or not self.email:
            return {
                "status": "manual_required",
                "notes": "Full name and email are required. Check your profile.",
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
                        "notes": f"Site presented a bot-challenge page. Visit {OPT_OUT_URL} manually.",
                    }

                # Fill confirmed field names from live page inspection
                def fill(name: str, value: str):
                    el = page.query_selector(f"input[name='{name}']")
                    if el and value:
                        el.fill(value)

                fill("name", self.full_name)
                fill("email", self.email)
                fill("phone", self.phone)
                fill("street", self.address)
                fill("city", self.city)
                fill("zip", self.zip_code)

                state_el = page.query_selector("select[name='state']")
                if state_el and self.state:
                    try:
                        state_el.select_option(label=self.state)
                    except Exception:
                        try:
                            state_el.select_option(value=self.state[:2].upper())
                        except Exception:
                            pass

                # Handle reCAPTCHA v2
                captcha_el = page.query_selector(
                    "iframe[src*='recaptcha'], .g-recaptcha, iframe[src*='captcha']"
                )
                if captcha_el:
                    site_key = extract_recaptcha_sitekey(page)
                    token = solve_recaptcha_v2(OPT_OUT_URL, site_key) if site_key else None

                    if not token:
                        browser.close()
                        return {
                            "status": "manual_required",
                            "notes": (
                                "reCAPTCHA detected. "
                                + ("Add CAPSOLVER_API_KEY to .env to automate this. "
                                   if not site_key else "CapSolver solve failed. ")
                                + f"Visit {OPT_OUT_URL} manually."
                            ),
                        }

                    inject_recaptcha_token(page, token)
                    page.wait_for_timeout(1000)

                submit_btn = page.query_selector("button[type='submit'], input[type='submit']")
                if submit_btn:
                    submit_btn.click()
                    page.wait_for_timeout(3000)
                    browser.close()
                    return {
                        "status": "submitted",
                        "notes": "Opt-out form submitted to ThatsThem.",
                    }

                browser.close()
                return {
                    "status": "manual_required",
                    "notes": f"Could not find submit button. Visit {OPT_OUT_URL} manually.",
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit {OPT_OUT_URL} manually.",
            }
