"""
CapSolver integration for automated CAPTCHA solving.

Supports:
  - reCAPTCHA v2 (checkbox)       → ReCaptchaV2TaskProxyLess
  - Cloudflare Turnstile (widget) → AntiTurnstileTaskProxyLess

Usage:
    from brokers.handlers.capsolver_helper import solve_recaptcha_v2, solve_turnstile

    token = solve_recaptcha_v2("https://example.com", site_key)
    token = solve_turnstile("https://example.com", site_key)

Returns None if CAPSOLVER_API_KEY is not set or solving fails.
"""
import time
import requests

# Loaded lazily so import never fails if config is missing
_API_KEY = None


def _get_api_key() -> str | None:
    global _API_KEY
    if _API_KEY is None:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        try:
            from config import CAPSOLVER_API_KEY
            _API_KEY = CAPSOLVER_API_KEY or ""
        except Exception:
            _API_KEY = ""
    return _API_KEY or None


def _create_task(task: dict) -> str | None:
    """Submit a task to CapSolver and return the task ID, or None on failure."""
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        resp = requests.post(
            "https://api.capsolver.com/createTask",
            json={"clientKey": api_key, "task": task},
            timeout=15,
        )
        data = resp.json()
        if data.get("errorId", 1) != 0:
            return None
        return data.get("taskId")
    except Exception:
        return None


def _poll_result(task_id: str, max_wait: int = 120) -> str | None:
    """Poll for the task result; return the solution token or None on timeout/error."""
    api_key = _get_api_key()
    if not api_key:
        return None
    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(3)
        try:
            resp = requests.post(
                "https://api.capsolver.com/getTaskResult",
                json={"clientKey": api_key, "taskId": task_id},
                timeout=15,
            )
            data = resp.json()
            if data.get("errorId", 1) != 0:
                return None
            status = data.get("status")
            if status == "ready":
                sol = data.get("solution", {})
                return sol.get("gRecaptchaResponse") or sol.get("token")
            # status == "processing" → keep polling
        except Exception:
            return None
    return None


def solve_recaptcha_v2(page_url: str, site_key: str) -> str | None:
    """
    Solve a reCAPTCHA v2 challenge.
    Returns the g-recaptcha-response token, or None if unavailable.
    """
    task_id = _create_task({
        "type": "ReCaptchaV2TaskProxyLess",
        "websiteURL": page_url,
        "websiteKey": site_key,
    })
    if not task_id:
        return None
    return _poll_result(task_id)


def solve_turnstile(page_url: str, site_key: str) -> str | None:
    """
    Solve a Cloudflare Turnstile challenge.
    Returns the cf-turnstile-response token, or None if unavailable.
    """
    task_id = _create_task({
        "type": "AntiTurnstileTaskProxyLess",
        "websiteURL": page_url,
        "websiteKey": site_key,
    })
    if not task_id:
        return None
    return _poll_result(task_id)


def inject_recaptcha_token(page, token: str):
    """Inject a solved reCAPTCHA v2 token into the page."""
    page.evaluate(f"""
        (function() {{
            var fields = document.querySelectorAll('[name="g-recaptcha-response"]');
            fields.forEach(function(el) {{ el.value = '{token}'; }});
        }})();
    """)


def inject_turnstile_token(page, token: str):
    """Inject a solved Turnstile token into the page."""
    page.evaluate(f"""
        (function() {{
            var fields = document.querySelectorAll('[name="cf-turnstile-response"]');
            fields.forEach(function(el) {{ el.value = '{token}'; }});
        }})();
    """)


def extract_recaptcha_sitekey(page) -> str | None:
    """Extract the reCAPTCHA v2 site key from the current page."""
    el = page.query_selector(".g-recaptcha[data-sitekey]")
    if el:
        return el.get_attribute("data-sitekey")
    # Also check iframe src
    frame = page.query_selector("iframe[src*='recaptcha']")
    if frame:
        src = frame.get_attribute("src") or ""
        for part in src.split("&"):
            if part.startswith("k=") or part.startswith("sitekey="):
                return part.split("=", 1)[1]
    return None


def extract_turnstile_sitekey(page) -> str | None:
    """Extract the Cloudflare Turnstile site key from the current page."""
    el = page.query_selector("[data-sitekey]")
    if el:
        return el.get_attribute("data-sitekey")
    # Check script tags for sitekey
    content = page.content()
    import re
    m = re.search(r"sitekey['\"]?\s*[:=]\s*['\"]([0-9a-zA-Z_\-]+)['\"]", content)
    return m.group(1) if m else None
