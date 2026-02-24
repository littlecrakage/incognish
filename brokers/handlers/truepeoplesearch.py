"""
TruePeopleSearch opt-out handler.
Flow: search for the person → grab their profile URL → submit removal.
Falls back to manual_required if Playwright is unavailable or profile not found.
"""
from brokers.handlers.base import BaseHandler


class Handler(BaseHandler):
    def submit(self) -> dict:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            return {
                "status": "manual_required",
                "notes": "Playwright not installed. Run: playwright install chromium. "
                         "Manual URL: https://www.truepeoplesearch.com/removal",
            }

        if not self.full_name or not self.state:
            return {
                "status": "manual_required",
                "notes": "First name, last name and state are required. Check your profile.",
            }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers({"User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )})

                # Step 1: Search for the person
                search_url = (
                    f"https://www.truepeoplesearch.com/results?"
                    f"name={self.full_name.replace(' ', '+')}"
                    f"&citystatezip={self.state}"
                )
                page.goto(search_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                # Find the first matching result card
                cards = page.query_selector_all("a.detail-block-link")
                if not cards:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": (
                            "No listings found automatically. "
                            "Visit https://www.truepeoplesearch.com/removal manually."
                        ),
                    }

                profile_url = cards[0].get_attribute("href")
                if not profile_url.startswith("http"):
                    profile_url = "https://www.truepeoplesearch.com" + profile_url

                # Step 2: Go to the removal page and submit
                page.goto("https://www.truepeoplesearch.com/removal", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                # Fill in the profile URL field
                url_input = page.query_selector("input[name='RecordPath'], input[placeholder*='URL'], input[type='url']")
                if url_input:
                    url_input.fill(profile_url)
                    submit_btn = page.query_selector("button[type='submit'], input[type='submit']")
                    if submit_btn:
                        submit_btn.click()
                        page.wait_for_timeout(3000)
                        browser.close()
                        return {
                            "status": "submitted",
                            "notes": f"Removal submitted for profile: {profile_url}",
                        }

                browser.close()
                return {
                    "status": "manual_required",
                    "notes": (
                        f"Found profile at {profile_url} but could not submit form automatically. "
                        "Visit https://www.truepeoplesearch.com/removal and paste that URL."
                    ),
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": (
                    f"Automation failed ({exc}). "
                    "Visit https://www.truepeoplesearch.com/removal manually."
                ),
            }
