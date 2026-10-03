"""Critical BluePrint browser journeys on disposable synthetic workspaces."""
from __future__ import annotations

import re
import pytest

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

    page.locator('nav a[data-page="work"]').focus()
    page.keyboard.press("Enter")
    expect(page.locator("#work-view")).to_be_visible()
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


def test_reader_is_observe_only_against_a_real_worklane_store(page: Page, action_workspace) -> None:
    _root, url = action_workspace
    page.goto(url + '/work-order?project=protocolcity&id=pc-1')
    expect(page.locator('#title')).to_have_text('Browser action fixture')
    expect(page.locator('#description')).to_contain_text('Synthetic write acceptance')
    expect(page.locator('#note-body')).to_have_count(0)
    expect(page.locator('#note-form')).to_have_count(0)
    expect(page.locator('#work-controls')).to_have_count(0)
    expect(page.locator('#action-priority')).to_have_count(0)


def test_work_order_reader_has_no_write_chrome(page: Page, healthy_base_url: str) -> None:
    page.goto(healthy_base_url + '/work-order?project=demo&id=demo-1')
    expect(page.locator('#title')).to_contain_text('Synthetic ready order')
    expect(page.locator('#note-body')).to_have_count(0)
    expect(page.locator('#note-form')).to_have_count(0)
    expect(page.locator('#work-controls')).to_have_count(0)
    expect(page.locator('h2', has_text='Comments')).to_be_visible()


@pytest.mark.parametrize('surface', ['overview', 'work'])
def test_failed_refresh_keeps_last_observation_visible(page: Page, healthy_base_url: str, surface: str) -> None:
    page.goto(healthy_base_url + ('/' if surface == 'overview' else '/work'))
    expect(page.locator('#freshness')).not_to_contain_text('Connecting')
    page.route(re.compile(r'.*/api/operations(?:\?.*)?$'), lambda route: route.abort())
    page.locator('#refresh').click()
    expect(page.locator('#freshness')).to_contain_text('Refresh failed')
    expect(page.locator(f'#{surface}-view')).to_be_visible()


def test_stale_heartbeat_is_visible_as_stale_evidence(page: Page) -> None:
    import tempfile
    from pathlib import Path
    from support.server import serve_binder
    from support.workspace import build_stale_workspace
    with tempfile.TemporaryDirectory(prefix='bp-browser-stale-') as tmp:
        with serve_binder(build_stale_workspace(Path(tmp))) as (url, _process):
            page.goto(url + '/connections')
            expect(page.locator('#connections-view')).to_contain_text('WorkForce heartbeat')
            expect(page.locator('#connections-view')).to_contain_text('stale')
            expect(page.locator('#connections-view')).to_contain_text('not a process health check')
