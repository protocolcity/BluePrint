"""Start overview/v1/serve.py on an ephemeral port for Playwright."""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

_CHECKOUT = Path(__file__).resolve().parents[2]
_SERVE = _CHECKOUT / "overview/v1/serve.py"


def pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_ready(port: int, timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/api/operations"
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"desk did not become ready on port {port}")


from contextlib import contextmanager


@contextmanager
def serve_binder(binder: Path):
    port = pick_port()
    import os

    env = {
        **os.environ,
        "PYTHONPATH": f"{_CHECKOUT / 'overview/v1'}:{_CHECKOUT / 'map/v1'}:{_CHECKOUT}",
    }
    installed_python = os.environ.get("BP_TEST_BLUEPRINT_PYTHON")
    if installed_python:
        if not Path(installed_python).is_absolute() or not Path(installed_python).is_file():
            raise ValueError("BP_TEST_BLUEPRINT_PYTHON must name an installed absolute interpreter")
        env.pop("PYTHONPATH", None)
        command = [installed_python, "-I", "-m", "overview.v1.serve"]
    else:
        command = [sys.executable, str(_SERVE)]
    command += ["--host", "127.0.0.1", "--port", str(port), "--binder", str(binder)]
    proc = subprocess.Popen(
        command,
        cwd=binder,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_ready(port)
        yield f"http://127.0.0.1:{port}", proc
    except Exception:
        proc.terminate()
        err = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(err or "server boot failed") from None
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
