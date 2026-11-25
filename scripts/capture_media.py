#!/usr/bin/env python3
"""Capture the documentation screenshots and the video clips of lab.meteo@uniparthenope.

Usage:
    LAB_CAPTURE_BASE=http://<host>:<port> python3 scripts/capture_media.py <jar-dir> docs/images media/clips [all|shots|clips]

<jar-dir> holds Netscape-format cookie jars named ``user1`` (a regular account) and ``admin``,
created by signing in with curl (``curl -c <jar-dir>/user1 …``). Use test accounts only: the
screenshots are published in the repository. The script never handles passwords. It needs
Playwright for Python and Google Chrome; it starts user1's runtime if it is not running.
"""
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

BASE = os.environ.get("LAB_CAPTURE_BASE", "http://localhost:8000").rstrip("/")
CAP = Path(sys.argv[1])          # holds the cookie jars
IMG = Path(sys.argv[2])          # docs/images
CLIPS = Path(sys.argv[3])        # media/clips
MODE = sys.argv[4] if len(sys.argv) > 4 else "all"
NB = "github/CCMMMA/lab-meteo-uniparthenope/demos/05_wind_forecast.ipynb"


def jar(name):
    cookies = []
    for line in (CAP / name).read_text().splitlines():
        parts = line.split("\t")
        if len(parts) == 7 and not line.startswith("# "):
            cookies.append({"name": parts[5], "value": parts[6], "domain": urlparse(BASE).hostname,
                            "path": parts[2], "httpOnly": True, "secure": False, "sameSite": "Lax"})
    return cookies


async def context(browser, user=None, video=False):
    kwargs = dict(viewport={"width": 1280, "height": 720}, device_scale_factor=1,
                  color_scheme="light", locale="en-GB")
    if video:
        kwargs.update(record_video_dir=str(CLIPS), record_video_size={"width": 1280, "height": 720})
    else:
        kwargs["viewport"] = {"width": 1280, "height": 800}
    ctx = await browser.new_context(**kwargs)
    # The strictly-necessary cookie notice has been read; keep it out of the frame.
    await ctx.add_init_script("try { localStorage.setItem('lab-cookie-notice', 'seen'); } catch (e) {}")
    if user:
        await ctx.add_cookies(jar(user))
    return ctx


async def run_all(page, timeout=240_000):
    """Run every cell from the keyboard (Shift+Enter), as a user would."""
    cells = page.locator(".jp-Notebook .jp-Cell")
    count = await cells.count()
    await cells.first.locator(".jp-InputPrompt").first.click()
    await page.keyboard.press("Escape")
    for _ in range(count):
        await page.keyboard.press("Shift+Enter")
        await page.wait_for_timeout(250)
    await page.wait_for_selector(".jp-OutputArea-output img", timeout=timeout)
    await page.wait_for_timeout(2500)


async def ensure_server(page):
    """Click-equivalent of Connect: start the runtime and wait until JupyterLab answers."""
    await page.goto(f"{BASE}/spawn/user1")
    await page.wait_for_url("**/user/user1/**", timeout=240_000)
    await page.wait_for_timeout(2000)


async def screenshots(browser):
    IMG.mkdir(parents=True, exist_ok=True)
    ctx = await context(browser)
    page = await ctx.new_page()
    await page.goto(f"{BASE}/services/demos/")
    await page.wait_for_timeout(1500)
    await page.screenshot(path=IMG / "gallery.png")
    await page.goto(f"{BASE}/login")
    await page.screenshot(path=IMG / "login.png")
    await page.goto(f"{BASE}/services/demos/lab/index.html?path=05_wind_forecast.ipynb")
    await page.wait_for_selector(".jp-Notebook", timeout=90_000)
    await page.wait_for_timeout(4000)
    await run_all(page)
    await page.wait_for_timeout(2000)
    await page.locator(".jp-OutputArea-output img").first.scroll_into_view_if_needed()
    await page.screenshot(path=IMG / "browser-runtime.png")
    await ctx.close()

    ctx = await context(browser, "user1")
    page = await ctx.new_page()
    await ensure_server(page)
    await page.goto(f"{BASE}/home")
    await page.wait_for_selector("#examples li a")
    await page.screenshot(path=IMG / "start-page.png")
    await page.click("#tab-github")
    await page.fill("#github-url", "https://github.com/CCMMMA/lab-meteo-uniparthenope/blob/main/demos/05_wind_forecast.ipynb")
    await page.screenshot(path=IMG / "open-from-github.png")
    await page.click("#tab-recent")
    await page.wait_for_timeout(2500)
    await page.screenshot(path=IMG / "recent.png")
    await page.goto(f"{BASE}/user/user1/notebooks/{NB}")
    await page.wait_for_selector(".jp-Notebook", timeout=60_000)
    await page.wait_for_timeout(3000)
    await run_all(page)
    await page.locator(".jp-OutputArea-output img").first.scroll_into_view_if_needed()
    await page.screenshot(path=IMG / "server-notebook.png")
    await page.goto(f"{BASE}/user/user1/lab")
    await page.wait_for_selector(".jp-DirListing", timeout=60_000)
    await page.wait_for_timeout(3000)
    await page.screenshot(path=IMG / "jupyterlab.png")
    await ctx.close()

    ctx = await context(browser, "admin")
    page = await ctx.new_page()
    await page.goto(f"{BASE}/dashboard")
    await page.wait_for_timeout(1500)
    await page.screenshot(path=IMG / "dashboard.png")
    await page.goto(f"{BASE}/privacy")
    await page.screenshot(path=IMG / "privacy.png")
    await ctx.close()


async def slow_scroll(page, total, steps=40, pause=90):
    for _ in range(steps):
        await page.mouse.wheel(0, total / steps)
        await page.wait_for_timeout(pause)


async def clips(browser):
    CLIPS.mkdir(parents=True, exist_ok=True)
    # 1. Gallery
    ctx = await context(browser, video=True)
    page = await ctx.new_page()
    await page.goto(f"{BASE}/services/demos/")
    await page.wait_for_timeout(2500)
    await slow_scroll(page, 2600, steps=60, pause=110)
    await page.wait_for_timeout(1000)
    await ctx.close()
    await page.video.save_as(CLIPS / "01-gallery.webm")

    # 2. Browser runtime (JupyterLite)
    ctx = await context(browser, video=True)
    page = await ctx.new_page()
    await page.goto(f"{BASE}/services/demos/lab/index.html?path=05_wind_forecast.ipynb")
    await page.wait_for_selector(".jp-Notebook", timeout=90_000)
    await page.wait_for_timeout(2000)
    await run_all(page)
    await page.locator(".jp-OutputArea-output img").first.scroll_into_view_if_needed()
    await page.wait_for_timeout(5000)
    await ctx.close()
    await page.video.save_as(CLIPS / "02-browser-runtime.webm")

    # 3. Start page: examples filter and GitHub
    ctx = await context(browser, "user1", video=True)
    page = await ctx.new_page()
    await page.goto(f"{BASE}/home")
    await page.wait_for_selector("#examples li a")
    await page.wait_for_timeout(2000)
    await page.click("#example-filter")
    await page.keyboard.type("forecast", delay=140)
    await page.wait_for_timeout(2000)
    await page.click("#tab-github")
    await page.wait_for_timeout(500)
    await page.click("#github-url")
    await page.keyboard.type("https://github.com/CCMMMA/lab-meteo-uniparthenope/blob/main/demos/05_wind_forecast.ipynb", delay=35)
    await page.wait_for_timeout(1500)
    await page.click("#tab-recent")
    await page.wait_for_timeout(3000)
    await ctx.close()
    await page.video.save_as(CLIPS / "03-start-page.webm")

    # 4. Server notebook (Notebook 7) running with the full scientific stack
    ctx = await context(browser, "user1", video=True)
    page = await ctx.new_page()
    await page.goto(f"{BASE}/user/user1/notebooks/{NB}")
    await page.wait_for_selector(".jp-Notebook", timeout=60_000)
    await page.wait_for_timeout(2500)
    await run_all(page)
    await page.locator(".jp-OutputArea-output img").first.scroll_into_view_if_needed()
    await page.wait_for_timeout(5000)
    await ctx.close()
    await page.video.save_as(CLIPS / "04-server-notebook.webm")

    # 5. JupyterLab workspace and 6. administration dashboard
    ctx = await context(browser, "user1", video=True)
    page = await ctx.new_page()
    await page.goto(f"{BASE}/user/user1/lab")
    await page.wait_for_selector(".jp-DirListing", timeout=60_000)
    await page.wait_for_timeout(5000)
    await ctx.close()
    await page.video.save_as(CLIPS / "05-jupyterlab.webm")

    ctx = await context(browser, "admin", video=True)
    page = await ctx.new_page()
    await page.goto(f"{BASE}/dashboard")
    await page.wait_for_timeout(2000)
    await slow_scroll(page, 1800, steps=50, pause=110)
    await page.wait_for_timeout(1000)
    await ctx.close()
    await page.video.save_as(CLIPS / "06-dashboard.webm")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        if MODE in ("all", "shots"):
            await screenshots(browser)
        if MODE in ("all", "clips"):
            await clips(browser)
        await browser.close()


asyncio.run(main())
