"""Run the packaged V1 surfaces without Homebrew-specific launchers."""
from importlib.resources import files
import runpy


def overview():
    runpy.run_path(str(files("overview.v1").joinpath("serve.py")), run_name="__main__")


def map_view():
    runpy.run_path(str(files("map.v1").joinpath("serve.py")), run_name="__main__")
