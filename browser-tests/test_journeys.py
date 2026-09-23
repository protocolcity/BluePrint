"""Critical BluePrint browser journeys on disposable synthetic workspaces."""
from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def test_lens_navigation_and_focus(page_healthy: Page, healthy_base_url: str) -> None:
    page = page_healthy
    expect(page.locator("#overview-view")).to_be_visible()
    expect(page.locator('nav a[data-page="overview"]')).to_be_visible()

    page.locator('nav a[data-page="work"]').click()
    expect(page.locator("#work-view")).to_be_visible()
    expect(page.locator("#page-title")).to_have_text("Work")

    page.locator('nav a[data-page="projects"]').click()
    expect(page.locator("#projects-view")).to_be_visible()

    page.locator('nav a[data-page="agents"]').click()
    expect(page.locator("#agents-view")).to_be_visible()

    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    page.locator('nav a[href="/map"]').click()
    expect(page.locator("#map-shell")).to_be_visible()
    expect(page.locator("#map-browser-list")).to_be_visible()

    page.locator('nav a[data-page="settings"]').click()
    expect(page.locator("#settings-view")).to_be_visible()


def test_work_search_and_supported_action_surfaces(page_healthy: Page) -> None:
    page = page_healthy
    page.locator('nav a[data-page="work"]').click()
    page.locator("#search").fill("Synthetic ready")
    page.locator("#search").press("Enter")
    expect(page.locator("#results")).to_contain_text(re.compile(r"matching work", re.I))
    expect(page.locator("#work-list, #work-band-act-now, #work-band-seat-backlog").first).to_be_visible()

    page.locator('nav a[data-page="overview"]').click()
    expect(page.locator("#for-you-decide-heading")).to_have_text("Act now")


def test_reader_return_and_work_order_detail(page_healthy: Page, healthy_base_url: str) -> None:
    page = page_healthy
    page.goto(f"{healthy_base_url}/work-order?project=demo&id=demo-1")
    expect(page.locator("#title")).to_contain_text("Synthetic ready order", timeout=15000)
    expect(page.locator("#reader-back")).to_have_attribute("href", "/work")
    page.locator("#reader-back").click()
    expect(page.locator("#work-view")).to_be_visible()


def test_map_browser_narrow_viewport(page_healthy: Page, healthy_base_url: str) -> None:
    page = page_healthy
    page.set_viewport_size({"width": 400, "height": 800})
    page.goto(f"{healthy_base_url}/map")
    expect(page.locator("#map-browser-list")).to_be_visible()
    expect(page.locator(".map-browser")).to_be_visible()
    page.locator("#map-browser-list").focus()


def test_projects_partial_store_is_visible(page_partial: Page) -> None:
    page = page_partial
    expect(page.locator("#projects-summary")).to_contain_text("unavailable")


def test_honest_empty_binder(page: Page) -> None:
    import tempfile
    from pathlib import Path

    from support.server import serve_binder
    from support.workspace import build_empty_workspace

    with tempfile.TemporaryDirectory(prefix="bp-browser-empty-") as tmp:
        binder = build_empty_workspace(Path(tmp))
        with serve_binder(binder) as (base_url, _proc):
            page.set_default_timeout(15000)
            page.goto(base_url + "/")
            expect(page.locator("#freshness")).not_to_contain_text("Connecting…", timeout=15000)
            page.goto(base_url + "/map")
            expect(page.locator("#map-browser-list")).to_be_visible()
