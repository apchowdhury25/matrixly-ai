"""Agents catalog page object."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from .base_page import BasePage


class AgentsPage(BasePage):
    def __init__(self, driver, base_url: str) -> None:
        super().__init__(driver, base_url, "agents")

    def deploy_buttons(self):
        return self.find_all_css("a.btn-primary")

    def shipping_card_deploy_is_last_cta(self) -> bool:
        """Shipping footer should end with Deploy Now (links above)."""
        cards = self.find_all_css("article.card-matrix")
        for card in cards:
            title = card.find_elements(By.CSS_SELECTOR, "h3")
            if not title or "Shipping" not in title[0].text:
                continue
            footer = card.find_elements(By.CSS_SELECTOR, "div.pt-4.border-t")
            if not footer:
                return False
            links = footer[-1].find_elements(By.CSS_SELECTOR, "a")
            if not links:
                return False
            last = links[-1]
            return "Deploy Now" in (last.text or "")
        return False

    def public_nav_links_admin(self) -> bool:
        """True if /admin is linked from header/nav/footer (authorized entry point)."""
        for a in self.find_all_css("header a, nav a, footer a"):
            href = (a.get_attribute("href") or "").lower()
            if href.rstrip("/").endswith("/admin") or "/admin" in href:
                return True
        return False
