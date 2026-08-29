"""Static-site smoke test: every page links locally, index configures an API, pages have content.

Run: python -m pytest tests/test_site.py
"""
from pathlib import Path
import re
import sys

SITE = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "help.html", "about.html", "privacy.html", "terms.html", "contact.html"]


def _read(name: str) -> str:
    return (SITE / name).read_text(encoding="utf-8")


def test_all_legal_pages_present():
    for p in PAGES:
        assert (SITE / p).exists(), f"missing {p}"


def test_every_page_has_title_and_meta_description():
    for p in PAGES:
        html = _read(p)
        assert "<title>" in html and "</title>" in html, f"{p} missing <title>"
        assert 'name="description"' in html, f"{p} missing meta description"


def test_index_has_api_endpoint_and_expected_lists():
    html = _read("index.html")
    assert "var API = " in html, "index must define the backend API var"
    for host in ["Instagram", "TikTok", "YouTube", "X/Twitter"]:
        assert host in html, f"index should advertise {host}"


def test_index_js_has_no_syntax_redflags():
    html = _read("index.html")
    # crude: balanced braces in the script block
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert scripts, "index must have an (inline) script block"
    for s in scripts:
        assert s.count("{") == s.count("}"), "unbalanced braces in inline JS"


def test_footer_links_resolve():
    html = _read("index.html")
    for target in PAGES:
        if target != "index.html":
            assert f'href="{target}"' in html, f"footer should link {target}"