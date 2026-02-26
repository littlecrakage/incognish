"""
FastPeopleSearch opt-out handler.
Flow: search → find profile URL → submit removal request.
Uses stealthy browser to bypass bot detection.
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall

OPT_OUT_URL = "https://www.fastpeoplesearch.com/removal"


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
                "notes": "Full name and state required. Check your profile.",
            }

        first = self.profile.get("first_name", "")
        last = self.profile.get("last_name", "")

        try:
            with sync_playwright() as p:
                browser, page = make_stealthy_page(p)

                # Step 1: Search
                search_url = (
                    f"https://www.fastpeoplesearch.com/name/{first}-{last}_{self.state}"
                ).replace(" ", "-")

                page.goto(search_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                if is_bot_wall(page.title()):
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Site blocked automated access (Cloudflare). Visit {OPT_OUT_URL} manually.",
                    }

                cards = page.query_selector_all("a.btn-primary, .card-block a[href*='/address/']")
                if not cards:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"No listing found automatically. Visit {OPT_OUT_URL} manually.",
                    }

                profile_url = cards[0].get_attribute("href")
                if not profile_url.startswith("http"):
                    profile_url = "https://www.fastpeoplesearch.com" + profile_url

                # Step 2: Removal form
                page.goto(OPT_OUT_URL, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                if is_bot_wall(page.title()):
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Removal page blocked by Cloudflare. Visit {OPT_OUT_URL} and paste: {profile_url}",
                    }

                url_input = page.query_selector(
                    "input[type='url'], input[name*='url'], input[name*='URL']"
                )
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
                    "notes": f"Found profile at {profile_url}. Visit {OPT_OUT_URL} and paste the URL.",
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit {OPT_OUT_URL} manually.",
            }
