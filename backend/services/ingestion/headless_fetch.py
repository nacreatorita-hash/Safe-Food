"""Python side of the headless fetcher (see tools/ministero_fetch.mjs)."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
SCRIPT = TOOLS_DIR / "ministero_fetch.mjs"


class FetchError(RuntimeError):
    pass


async def fetch_many(urls: list[str], timeout: float = 180.0) -> dict[str, dict[str, Any]]:
    """Fetch URLs through a real browser session. Returns {url: {status, text|file|error}}."""
    if not urls:
        return {}
    env = os.environ.copy()
    env.setdefault("MINISTERO_PLAYWRIGHT_MODULE", os.environ.get("MINISTERO_PLAYWRIGHT_MODULE", "playwright"))
    env.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers"))
    proc = await asyncio.create_subprocess_exec(
        "node", str(SCRIPT), json.dumps(urls),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        proc.kill()
        raise FetchError("timeout del browser headless") from exc
    if proc.returncode != 0:
        raise FetchError(stderr.decode(errors="ignore")[-400:] or "browser headless terminato con errore")
    try:
        return json.loads(stdout.decode())
    except json.JSONDecodeError as exc:
        raise FetchError("output non valido dal fetcher headless") from exc
