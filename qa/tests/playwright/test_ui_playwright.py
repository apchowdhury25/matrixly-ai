"""Playwright UI smoke suite."""

from __future__ import annotations

import pytest

from config import PUBLIC_PAGES


@pytest.mark.playwright
@pytest.mark.smoke
class TestPublicPagesPlaywright:
    def test_each_public_page_has_title(self, page, site_base_url):
        for name in PUBLIC_PAGES:
            page.goto(f"{site_base_url}/{name}", wait_until="domcontentloaded")
            title = page.title()
            assert title and len(title) > 2, f"{name} missing title"

    def test_agents_grid_cards(self, page, site_base_url):
        page.goto(f"{site_base_url}/agents.html", wait_until="domcontentloaded")
        cards = page.locator("article.card-matrix")
        assert cards.count() >= 6
        deploy = page.locator('a.btn-primary:has-text("Deploy Now")')
        assert deploy.count() >= 4

    def test_shipping_deploy_align_structure(self, page, site_base_url):
        page.goto(f"{site_base_url}/agents.html", wait_until="domcontentloaded")
        shipping = page.locator("article.card-matrix").filter(has_text="Shipping Assistant")
        assert shipping.count() >= 1
        footer = shipping.locator("div.pt-4.border-t").last
        text = footer.inner_text()
        assert "Deploy Now" in text
        # Links should not appear after Deploy Now inside the same footer-only block
        # User guide lives above the bordered footer
        assert shipping.locator('a:has-text("User guide")').count() >= 1

    def test_admin_gate(self, page, site_base_url):
        page.goto(f"{site_base_url}/Admin.html", wait_until="domcontentloaded")
        assert page.locator("#gate").is_visible()
        assert page.locator("#app").is_hidden() or "hidden" in (
            page.locator("#app").get_attribute("class") or ""
        )
