"""
BeenVerified opt-out handler.
Flow: search by name/state → select record → solve Turnstile → submit.
Email verification is required to finalize removal.
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall
from brokers.handlers.capsolver_helper import (
    extract_turnstile_sitekey, solve_turnstile, inject_turnstile_token,
)

SEARCH_URL = "https://www.beenverified.com/app/optout/search"
OPT_OUT_URL = "https://www.beenverified.com/app/optout/search"


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

        try:
            with sync_playwright() as p:
                browser, page = make_stealthy_page(p)

                page.goto(SEARCH_URL, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                # Solve Turnstile if present
                if not self._maybe_solve_turnstile(page, SEARCH_URL):
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Cloudflare Turnstile could not be solved. Visit {OPT_OUT_URL} manually.",
                    }

                # Fill the search form
                first = self.profile.get("first_name", "")
                last = self.profile.get("last_name", "")

                first_el = page.query_selector("input[name='firstName'], input[placeholder*='First']")
                last_el  = page.query_selector("input[name='lastName'],  input[placeholder*='Last']")
                state_el = page.query_selector("select[name='state'], input[name='state']")

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

                submit = page.query_selector("button[type='submit'], input[type='submit']")
                if not submit:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Could not find search form. Visit {OPT_OUT_URL} manually.",
                    }

                submit.click()
                page.wait_for_load_state("networkidle", timeout=20000)

                # Select the first result
                result = (
                    page.query_selector("a:has-text('Opt Out')")
                    or page.query_selector("button:has-text('Opt Out')")
                    or page.query_selector(".optout-btn, .opt-out-btn")
                )
                if result:
                    result.click()
                    page.wait_for_load_state("networkidle", timeout=20000)

                # Fill email on the opt-out confirmation form
                email_el = page.query_selector("input[type='email'], input[name='email']")
                if email_el and self.email:
                    email_el.fill(self.email)
                    confirm = page.query_selector("button[type='submit'], input[type='submit']")
                    if confirm:
                        confirm.click()
                        page.wait_for_timeout(3000)

                browser.close()
                return {
                    "status": "submitted",
                    "notes": (
                        "Opt-out submitted to BeenVerified. "
                        "Check your email and click the verification link to complete removal."
                    ),
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit {OPT_OUT_URL} manually.",
            }

    def _maybe_solve_turnstile(self, page, url: str) -> bool:
        """If a Turnstile is present, solve it via CapSolver. Returns True if clear to proceed."""
        turnstile = page.query_selector("[data-sitekey], iframe[src*='challenges.cloudflare']")
        if not turnstile:
            return True  # No Turnstile — proceed normally

        site_key = extract_turnstile_sitekey(page)
        token = solve_turnstile(url, site_key) if site_key else None
        if not token:
            return False

        inject_turnstile_token(page, token)
        page.wait_for_timeout(2000)
        return True
