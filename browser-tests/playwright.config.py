"""Playwright pytest configuration — synthetic fixtures only; no live workspace."""
from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

pytest_plugins = ("pytest_playwright",)


def pytest_configure(config):
    ARTIFACTS.mkdir(exist_ok=True)


def pytest_playwright_configure(playwright):
    playwright.selectors.set_test_id_attribute("data-testid")


def pytest_addoption(parser):
    parser.addoption(
        "--bp-base-url",
        action="store",
        default="",
        help="Running desk base URL (set by conftest when absent)",
    )
