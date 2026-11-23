"""Input validation (RegEx) and XSS-safe text cleaning.

XSS PREVENTION (defence in depth):
1. clean_text() strips HTML tags and control characters from every free-text
   field before it is stored.
2. The Nuxt/Vue frontend escapes all {{ }} output by default and never uses v-html.
3. The API sends strict security headers (see main.py) including a CSP.
"""
import re
from urllib.parse import urlparse

TAG_RE = re.compile(r"<[^>]*>")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SCRIPT_HINT_RE = re.compile(r"(javascript:|data:text/html|on\w+\s*=)", re.IGNORECASE)

# Titles: letters, numbers, spaces and common punctuation only.
TITLE_RE = re.compile(r"^[\w\s.,:;!?&()'\"/+\-#@%]{3,150}$", re.UNICODE)
NAME_RE = re.compile(r"^[A-Za-zÀ-ÿ0-9 .,'\-]{2,100}$")
# Philippine mobile (09XXXXXXXXX or +639XXXXXXXXX) or Manila landline-ish digits.
PH_PHONE_RE = re.compile(r"^(?:\+63|0)9\d{9}$")
SKILL_RE = re.compile(r"^[A-Za-z0-9 .+#\-]{2,30}$")
CATEGORY_RE = re.compile(r"^[A-Za-z &/\-]{3,40}$")
PSGC_CODE_RE = re.compile(r"^\d{9,10}$")
REFERENCE_RE = re.compile(r"^[A-Za-z0-9\-_/ ]{3,60}$")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

CATEGORIES = [
    "Graphic Design", "Proofreading & Editing", "Tutoring", "Writing",
    "Presentation Design", "Video & Animation", "Programming Help",
    "Research Assistance", "Translation", "Other",
]


def clean_text(value: str) -> str:
    """Remove HTML tags / control characters and trim whitespace."""
    value = CONTROL_RE.sub("", value)
    value = TAG_RE.sub("", value)
    return value.strip()


def assert_safe_text(value: str, field: str = "text") -> str:
    value = clean_text(value)
    if SCRIPT_HINT_RE.search(value):
        raise ValueError(f"{field} contains disallowed content")
    return value


def validate_deliverable_url(url: str) -> str:
    """Deliverables must be an https link (Google Drive, Dropbox, OneDrive ...)."""
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or len(url) > 500:
        raise ValueError("Link must be a valid https:// URL")
    if SCRIPT_HINT_RE.search(url) or any(c in url for c in "<>\"' "):
        raise ValueError("Link contains disallowed characters")
    return url


def is_uuid(value: str) -> bool:
    return bool(UUID_RE.match(value))
