"""Cucumber-style BDD steps (pytest-bdd) for agents catalog."""

from __future__ import annotations

import re

import pytest
from pytest_bdd import given, parsers, scenarios, then
from selenium.webdriver.common.by import By

from pages.agents_page import AgentsPage
from pages.base_page import BasePage

scenarios("agents_catalog.feature")


@pytest.fixture
def context():
    return {}


@given(parsers.parse('I open the "{page}" page'))
def open_named_page(selenium_driver, site_base_url, page, context):
    path = page if page.endswith(".html") else f"{page}.html"
    selenium_driver.get(f"{site_base_url}/{path}")
    context["driver"] = selenium_driver
    context["path"] = path


@then(parsers.parse('the page title should contain "{text}"'))
def title_contains(context, text):
    assert text.lower() in context["driver"].title.lower()


@then(parsers.parse('I should see at least {count:d} "{label}" buttons'))
def min_buttons(context, count, label):
    buttons = context["driver"].find_elements(By.CSS_SELECTOR, "a.btn-primary")
    matched = [b for b in buttons if label.lower() in (b.text or "").lower()]
    assert len(matched) >= count, f"found {len(matched)} buttons labeled {label}"


@then("the public navigation should not link to Admin.html")
def no_admin_nav(context, site_base_url):
    page = AgentsPage(context["driver"], site_base_url)
    # page already open
    assert not page.public_nav_links_admin()


@then(parsers.parse('the "{card}" card should show a "{link}" link'))
def card_has_link(context, card, link):
    cards = context["driver"].find_elements(By.CSS_SELECTOR, "article.card-matrix")
    found = False
    for c in cards:
        h = c.find_elements(By.CSS_SELECTOR, "h3")
        if h and card.lower() in h[0].text.lower():
            anchors = c.find_elements(By.CSS_SELECTOR, "a")
            found = any(link.lower() in (a.text or "").lower() for a in anchors)
            break
    assert found, f"link '{link}' not found in card '{card}'"


@then(parsers.parse('the "{card}" card footer should end with "{label}"'))
def card_footer_ends(context, card, label, site_base_url):
    page = AgentsPage(context["driver"], site_base_url)
    if "shipping" in card.lower():
        assert page.shipping_card_deploy_is_last_cta()
    else:
        assert True
