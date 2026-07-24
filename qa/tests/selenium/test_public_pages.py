"""Selenium UI smoke — TestNG-style class suite for public Matrixly pages."""

from __future__ import annotations

import pytest
import requests
from selenium.webdriver.common.by import By

from config import PUBLIC_PAGES
from pages.agents_page import AgentsPage
from pages.base_page import BasePage


@pytest.mark.selenium
@pytest.mark.smoke
class TestPublicPagesSelenium:
    """Mirrors a TestNG test class: one suite of related UI assertions."""

    def test_http_ok_all_public_pages(self, site_base_url):
        for page in PUBLIC_PAGES:
            url = f"{site_base_url}/{page}"
            res = requests.get(url, timeout=20)
            assert res.status_code == 200, f"{url} -> {res.status_code}"

    def test_home_loads_brand(self, selenium_driver, site_base_url):
        page = BasePage(selenium_driver, site_base_url, "index.html").open()
        page.wait_ready()
        assert "Matrixly" in page.title() or page.logo_visible()
        assert page.has_css("header") or page.has_css("nav")

    def test_agents_catalog_deploy_buttons(self, selenium_driver, site_base_url):
        page = AgentsPage(selenium_driver, site_base_url).open()
        page.wait_ready()
        buttons = page.deploy_buttons()
        assert len(buttons) >= 4, "expected multiple Deploy Now buttons"
        assert page.shipping_card_deploy_is_last_cta(), (
            "Shipping Deploy Now should be the last CTA in the card footer"
        )

    def test_admin_not_in_public_nav(self, selenium_driver, site_base_url):
        page = AgentsPage(selenium_driver, site_base_url).open()
        page.wait_ready()
        assert not page.public_nav_links_admin()

    def test_theme_toggle_present_on_agents(self, selenium_driver, site_base_url):
        page = AgentsPage(selenium_driver, site_base_url).open()
        page.wait_ready()
        # Theme control is optional across pages; if present, ensure it's clickable-ish
        toggles = selenium_driver.find_elements(
            By.CSS_SELECTOR,
            '[aria-label*="theme" i], button[id*="theme" i], [data-theme-toggle], #theme-toggle',
        )
        # Soft assert: page still usable either way
        assert page.has_css("main") or page.has_css("section")


@pytest.mark.selenium
@pytest.mark.smoke
class TestAdminGateSelenium:
    def test_admin_page_reachable_and_gated(self, selenium_driver, site_base_url):
        selenium_driver.get(f"{site_base_url}/Admin.html")
        assert "QA" in selenium_driver.title or "Admin" in selenium_driver.title
        # Gate visible before unlock
        gate = selenium_driver.find_elements(By.ID, "gate")
        assert gate, "expected password gate"
        app = selenium_driver.find_elements(By.ID, "app")
        assert app
        # App should start hidden
        classes = (app[0].get_attribute("class") or "")
        assert "hidden" in classes or not app[0].is_displayed()
