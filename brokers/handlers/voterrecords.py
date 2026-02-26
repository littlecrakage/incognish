"""
VoterRecords opt-out handler.
Flow: search by name/state → navigate to profile → click opt-out link → submit form.
Email verification may be required to complete removal (not always sent).
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
                         "Manual URL: https://voterrecords.com/opt-out",
            }

        if not self.full_name or not self.state:
            return {
                "status": "manual_required",
                "notes": "Full name and state are required. Check your profile.",
            }

        first = self.profile.get("first_name", "")
        last = self.profile.get("last_name", "")
        state_slug = self.state.lower().replace(" ", "-")

        try:
            with sync_playwright() as p:
                browser, page = make_stealthy_page(p)

                # Step 1: Search by name + state
                name_slug = f"{first.lower()}-{last.lower()}".replace(" ", "-")
                search_url = f"https://voterrecords.com/voters/{name_slug}/{state_slug}"
                page.goto(search_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                if is_bot_wall(page.title()):
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": "Site is protected by Cloudflare and blocks automated access. "
                                 "Visit https://voterrecords.com/opt-out manually: "
                                 "search your name, open your record, scroll to bottom, click 'Record Opt-Out'.",
                    }

                # Find first voter record link
                result_links = page.query_selector_all("a[href*='/voter/']")

                if not result_links:
                    # Fallback: try the opt-out search form
                    page.goto("https://voterrecords.com/opt-out", timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=20000)

                    name_input = page.query_selector(
                        "input[name='name'], input[name='q'], input[placeholder*='Name']"
                    )
                    if name_input:
                        name_input.fill(self.full_name)
                        state_sel = page.query_selector("select[name='state'], input[name='state']")
                        if state_sel:
                            tag = state_sel.evaluate("el => el.tagName.toLowerCase()")
                            if tag == "select":
                                try:
                                    state_sel.select_option(label=self.state)
                                except Exception:
                                    state_sel.select_option(value=self.state[:2].upper())
                            else:
                                state_sel.fill(self.state)
                        submit = page.query_selector("button[type='submit'], input[type='submit']")
                        if submit:
                            submit.click()
                            page.wait_for_load_state("networkidle", timeout=20000)
                            result_links = page.query_selector_all("a[href*='/voter/']")

                if not result_links:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": "No voter record found automatically. "
                                 "Visit https://voterrecords.com/opt-out manually.",
                    }

                # Step 2: Go to the first matching profile
                profile_url = result_links[0].get_attribute("href")
                if not profile_url.startswith("http"):
                    profile_url = "https://voterrecords.com" + profile_url

                page.goto(profile_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)

                # Step 3: Find the opt-out link (usually at the bottom of the page)
                opt_out_link = (
                    page.query_selector("a[href*='opt-out']")
                    or page.query_selector("a:has-text('Opt Out')")
                    or page.query_selector("a:has-text('opt out')")
                    or page.query_selector("a:has-text('Remove')")
                )

                if not opt_out_link:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": (
                            f"Found profile at {profile_url} but could not locate the opt-out link. "
                            "Scroll to the bottom of your record page and click 'Record Opt-Out'."
                        ),
                    }

                opt_out_link.click()
                page.wait_for_load_state("networkidle", timeout=20000)

                # Check for CAPTCHA
                captcha = page.query_selector(
                    "iframe[src*='recaptcha'], .g-recaptcha, iframe[src*='captcha']"
                )
                if captcha:
                    browser.close()
                    return {
                        "status": "manual_required",
                        "notes": (
                            f"CAPTCHA detected. Visit {page.url} to complete the opt-out. "
                            f"Your profile: {profile_url}"
                        ),
                    }

                # Step 4: Fill form fields
                email_input = page.query_selector(
                    "input[type='email'], input[name='email'], input[name*='email']"
                )
                if email_input and self.email:
                    email_input.fill(self.email)

                url_input = page.query_selector(
                    "input[name*='url'], input[name*='URL'], input[name*='link'], input[type='url']"
                )
                if url_input:
                    url_input.fill(profile_url)

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
                            f"Opt-out submitted for {profile_url}. "
                            "If you receive a verification email, click the link to complete removal."
                        ),
                    }

                browser.close()
                return {
                    "status": "manual_required",
                    "notes": (
                        f"Could not submit opt-out form. "
                        f"Visit https://voterrecords.com/opt-out manually. Profile: {profile_url}"
                    ),
                }

        except Exception as exc:
            return {
                "status": "manual_required",
                "notes": f"Automation failed ({exc}). Visit https://voterrecords.com/opt-out manually.",
            }
