"""
SmartBackgroundChecks opt-out handler.
Flow: search by name/state → navigate to profile → click removal button.
An email confirmation may be sent to verify the removal.
"""
from brokers.handlers.base import BaseHandler, make_stealthy_page, is_bot_wall


class Handler(BaseHandler):
    def submit(self) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "status": "manual_required",
                "notes": "Playwright not installed. Run: playwright install chromium. "
                         "Manual URL: https://www.smartbackgroundchecks.com/optout",
            }

        if not self.full_name or not self.state:
            return {
                "status": "manual_required",
                "notes": "Full name and state are required. Check your profile.",
            }

        first = self.profile.get("first_name", "")
        last = self.profile.get("last_name", "")
        state_slug = self.state.replace(" ", "-")

        try:
            with sync_playwright() as p:
                browser, page = make_stealthy_page(p)

                # Step 1: Search for the person's listing
                name_slug = f"{first}-{last}".replace(" ", "-")
                search_url = (
                    f"https://www.smartbackgroundchecks.com/people/{name_slug}/{state_slug}"
                )
                page.goto(search_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                if is_bot_wall(page.title()):
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": "Site is protected by Cloudflare and blocks automated access. "
                                 "Visit https://www.smartbackgroundchecks.com/optout manually: "
                                 "search your name, open your listing, click 'Request My Record To Be Removed'.",
                    }

                # Find a result card link
                result_links = (
                    page.query_selector_all("a[href*='/people/']")
                    or page.query_selector_all(".result a, .card a, .person-card a")
                )
                # Filter out the search URL itself
                profile_url = None
                for link in result_links:
                    href = link.get_attribute("href") or ""
                    if "/people/" in href and state_slug.lower() in href.lower():
                        profile_url = href
                        break
                if not profile_url and result_links:
                    profile_url = result_links[0].get_attribute("href")

                if not profile_url:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": "No listing found automatically. "
                                 "Visit https://www.smartbackgroundchecks.com/optout manually.",
                    }

                if not profile_url.startswith("http"):
                    profile_url = "https://www.smartbackgroundchecks.com" + profile_url

                # Step 2: Go to the profile page
                page.goto(profile_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                # Step 3: Click the removal button
                remove_btn = (
                    page.query_selector("a:has-text('Remove')")
                    or page.query_selector("button:has-text('Remove')")
                    or page.query_selector("a:has-text('Opt Out')")
                    or page.query_selector("a[href*='optout'], a[href*='opt-out']")
                )

                if not remove_btn:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": (
                            f"Found profile at {profile_url} but could not locate the removal button. "
                            "Click 'Request My Record To Be Removed' on that page."
                        ),
                    }

                remove_btn.click()
                page.wait_for_load_state("networkidle", timeout=20000)

                # Step 4: Fill email if an opt-out form appears after clicking
                email_input = page.query_selector(
                    "input[type='email'], input[name='email'], input[name*='email']"
                )
                if email_input and self.email:
                    email_input.fill(self.email)
                    submit_btn = page.query_selector(
                        "button[type='submit'], input[type='submit']"
                    )
                    if submit_btn:
                        submit_btn.click()
                        page.wait_for_timeout(3000)

                browser.close()
                return {
                    "status": "submitted",
                    "notes": (
                        f"Removal request submitted for {profile_url}. "
                        "Check your email and click the verification link if received."
                    ),
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": (
                    f"Automation failed ({exc}). "
                    "Visit https://www.smartbackgroundchecks.com/optout manually."
                ),
            }
