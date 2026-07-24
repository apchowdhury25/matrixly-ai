"""Playwright browser fixture (does not require global pytest-playwright plugin)."""

from __future__ import annotations

import pytest

from config import playwright_headless, timeout_ms


@pytest.fixture(scope="session")
def browser_type_launch_args():
    return {"headless": playwright_headless()}


@pytest.fixture(scope="session")
def pw_browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=playwright_headless())
        yield browser
        browser.close()


@pytest.fixture
def page(pw_browser, site_base_url):
    context = pw_browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.set_default_timeout(timeout_ms())
    page._site_base_url = site_base_url  # type: ignore[attr-defined]
    yield page
    context.close()
