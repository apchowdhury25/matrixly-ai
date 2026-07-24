"""Base page object for Selenium."""

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class BasePage:
    def __init__(self, driver: WebDriver, base_url: str, path: str = "") -> None:
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.path = path.lstrip("/")

    def open(self) -> "BasePage":
        self.driver.get(f"{self.base_url}/{self.path}" if self.path else self.base_url)
        return self

    def title(self) -> str:
        return self.driver.title

    def wait_ready(self, timeout: float = 10) -> None:
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def find_css(self, selector: str):
        return self.driver.find_element(By.CSS_SELECTOR, selector)

    def find_all_css(self, selector: str):
        return self.driver.find_elements(By.CSS_SELECTOR, selector)

    def has_css(self, selector: str) -> bool:
        return len(self.find_all_css(selector)) > 0

    def wait_css(self, selector: str, timeout: float = 10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def logo_visible(self) -> bool:
        # Brand logo / home link patterns used across Matrixly pages
        selectors = [
            'a[href="/"] img[src*="matrixly-logo"]',
            'a.nav-brand img[src*="matrixly-logo"]',
            'img[alt="Matrixly"]',
            "a.nav-brand img",
            'header img[src*="matrixly-logo"]',
        ]
        return any(self.has_css(s) for s in selectors)

    def nav_has_agents(self) -> bool:
        return any(
            "agents" in (a.get_attribute("href") or "").lower()
            for a in self.find_all_css("header a, nav a")
        )
