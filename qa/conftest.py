"""Pytest fixtures — Selenium + shared options."""

from __future__ import annotations

import os

import pytest

from config import base_url, headless, selenium_browser, timeout_ms


def pytest_addoption(parser: pytest.Parser) -> None:
    # Use --site-url to avoid clashing with pytest-playwright's --base-url
    parser.addoption(
        "--site-url",
        action="store",
        default=None,
        help="Site base URL (overrides BASE_URL env)",
    )


@pytest.fixture(scope="session")
def site_base_url(pytestconfig: pytest.Config) -> str:
    site = pytestconfig.getoption("site_url")
    if site:
        return str(site).rstrip("/")
    # Honor pytest-playwright / common --base-url if present
    try:
        base = pytestconfig.getoption("base_url")
        if base:
            return str(base).rstrip("/")
    except Exception:
        pass
    env = os.getenv("BASE_URL")
    if env:
        return env.rstrip("/")
    return base_url()


@pytest.fixture(scope="session")
def selenium_driver():
    """Session-scoped Selenium WebDriver (Chrome by default, headless in CI)."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager

    browser = selenium_browser()
    driver = None

    if browser == "firefox":
        opts = FirefoxOptions()
        if headless():
            opts.add_argument("-headless")
        driver = webdriver.Firefox(
            service=FirefoxService(GeckoDriverManager().install()),
            options=opts,
        )
    else:
        opts = ChromeOptions()
        if headless():
            opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1440,900")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=opts,
        )

    driver.set_page_load_timeout(timeout_ms() / 1000.0)
    driver.implicitly_wait(3)
    yield driver
    driver.quit()


@pytest.fixture
def open_page(selenium_driver, site_base_url):
    """Helper: open a relative path and return the driver."""

    def _open(path: str):
        path = path.lstrip("/")
        selenium_driver.get(f"{site_base_url}/{path}")
        return selenium_driver

    return _open
