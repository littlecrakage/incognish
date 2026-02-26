"""
ClustrMaps opt-out handler.
Flow: navigate to opt-out page → solve Turnstile → fill email → click Next Step.
The submit button is disabled until Turnstile passes via onTurnstileSuccess(token).
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall
from brokers.handlers.capsolver_helper import (
    extract_turnstile_sitekey, solve_turnstile, inject_turnstile_token,
)

OPT_OUT_URL = "https://clustrmaps.com/bl/opt-out"


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
                        "notes": f"Site blocked automated access (Cloudflare). Visit {OPT_OUT_URL} manually.",
                    }

                # Solve Turnstile — ClustrMaps gates the submit button on onTurnstileSuccess()
                site_key = extract_turnstile_sitekey(page)
                if site_key:
                    token = solve_turnstile(OPT_OUT_URL, site_key)
                    if not token:
                        browser.close()
                        return {
                            "status": "manual_required",
                            "notes": f"Turnstile could not be solved. Visit {OPT_OUT_URL} manually.",
                        }
                    # Inject token into the hidden field AND call the site callback to unlock the button
                    inject_turnstile_token(page, token)
                    page.evaluate(f"if (typeof onTurnstileSuccess === 'function') onTurnstileSuccess('{token}')")
                    page.wait_for_timeout(1500)

                # Fill email
                email_el = page.query_selector("input[type='email'], input[name='email'], input[placeholder*='mail' i]")
                if not email_el:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Could not find email field. Visit {OPT_OUT_URL} manually.",
                    }
                email_el.fill(self.email)

                # Click submit (button may be .submit-comment or type=submit)
                submit = (
                    page.query_selector("button.submit-comment")
                    or page.query_selector("button[type='submit']")
                    or page.query_selector("input[type='submit']")
                )
                if not submit:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Could not find submit button. Visit {OPT_OUT_URL} manually.",
                    }

                submit.click()
                page.wait_for_timeout(4000)

                browser.close()
                return {
                    "status": "submitted",
                    "notes": (
                        "Opt-out request submitted to ClustrMaps. "
                        "Check your email inbox for a confirmation link to complete removal."
                    ),
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit {OPT_OUT_URL} manually.",
            }
