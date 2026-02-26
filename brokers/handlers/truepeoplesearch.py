"""
TruePeopleSearch opt-out handler.
Flow: search for the person → grab profile URL → submit removal.
Uses stealthy browser to bypass bot detection.
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall

OPT_OUT_URL = "https://www.truepeoplesearch.com/removal"


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
                "notes": "First name, last name and state are required. Check your profile.",
            }

        try:
            with sync_playwright() as p:
                browser, page = make_stealthy_page(p)

                # Step 1: Search for the person
                search_url = (
                    f"https://www.truepeoplesearch.com/results?"
                    f"name={self.full_name.replace(' ', '+')}&citystatezip={self.state}"
                )
                page.goto(search_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                if is_bot_wall(page.title()):
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Site blocked automated access (Cloudflare). Visit {OPT_OUT_URL} manually.",
                    }

                cards = page.query_selector_all("a.detail-block-link")
                if not cards:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"No listings found automatically. Visit {OPT_OUT_URL} manually.",
                    }

                profile_url = cards[0].get_attribute("href")
                if not profile_url.startswith("http"):
                    profile_url = "https://www.truepeoplesearch.com" + profile_url

                # Step 2: Submit removal form
                page.goto(OPT_OUT_URL, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                if is_bot_wall(page.title()):
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": f"Removal page blocked by Cloudflare. Visit {OPT_OUT_URL} and paste: {profile_url}",
                    }

                url_input = page.query_selector(
                    "input[name='RecordPath'], input[placeholder*='URL'], input[type='url']"
                )
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
                    "notes": f"Found profile at {profile_url} but could not submit form. Visit {OPT_OUT_URL} and paste that URL.",
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit {OPT_OUT_URL} manually.",
            }
