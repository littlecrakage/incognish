"""
FastPeopleSearch opt-out handler.
Flow: search → find profile URL → submit removal request.
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
                         "Manual URL: https://www.fastpeoplesearch.com/removal",
            }

        if not self.full_name or not self.state:
            return {
                "status": "manual_required",
                "notes": "Full name and state required. Check your profile.",
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

                # Search
                first = self.profile.get("first_name", "")
                last = self.profile.get("last_name", "")
                search_url = (
                    f"https://www.fastpeoplesearch.com/name/{first}-{last}_{self.state}"
                ).replace(" ", "-")

                page.goto(search_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                # Grab first result link
                cards = page.query_selector_all("a.btn-primary, .card-block a[href*='/address/']")
                if not cards:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": "No listing found automatically. "
                                 "Visit https://www.fastpeoplesearch.com/removal manually.",
                    }

                profile_url = cards[0].get_attribute("href")
                if not profile_url.startswith("http"):
                    profile_url = "https://www.fastpeoplesearch.com" + profile_url

                # Removal page
                page.goto("https://www.fastpeoplesearch.com/removal", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                url_input = page.query_selector("input[type='url'], input[name*='url'], input[name*='URL']")
                if url_input:
                    url_input.fill(profile_url)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(3000)
                    browser.close()
                    return {
                        "status": "submitted",
                        "notes": f"Removal submitted for: {profile_url}",
                    }

                browser.close()
                return {
                    "status": "manual_required",
                    "notes": (
                        f"Found profile at {profile_url}. "
                        "Visit https://www.fastpeoplesearch.com/removal and paste the URL."
                    ),
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit https://www.fastpeoplesearch.com/removal manually.",
            }
