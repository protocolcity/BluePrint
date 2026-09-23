"""Shared Playwright fixtures."""
from __future__ import annotations

import tempfile
from contextlib import contextmanager

import pytest

from support.server import serve_binder
from support.workspace import build_healthy_workspace, build_partial_workspace


@contextmanager
def _desk(binder_builder):
    with tempfile.TemporaryDirectory(prefix="bp-browser-") as tmp:
        binder = binder_builder(__import__("pathlib").Path(tmp))
        with serve_binder(binder) as (base_url, _proc):
            yield base_url


@pytest.fixture(scope="session")
def healthy_base_url():
    with _desk(build_healthy_workspace) as url:
        yield url


@pytest.fixture(scope="session")
def partial_base_url():
    with _desk(build_partial_workspace) as url:
        yield url


@pytest.fixture
def page_healthy(page, healthy_base_url):
    page.set_default_timeout(15000)
    page.goto(healthy_base_url + "/")
    return page


@pytest.fixture
def page_partial(page, partial_base_url):
    page.set_default_timeout(15000)
    page.goto(partial_base_url + "/projects")
    return page
