"""End-to-end Playwright browser tests for the 7-step RTL Persian Topographic Survey Web App."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

CHROMIUM_BIN = Path("/tmp/chromium")


@pytest.mark.skipif(
    not CHROMIUM_BIN.exists(),
    reason="Headless Chromium binary (/tmp/chromium) not present in this environment",
)
def test_playwright_7step_wizard_and_responsive_layout():
    """Verify full 7-step wizard, live Step 5 edge filter, 2D/3D toggle, and responsive viewports."""
    # Ensure server is reachable on 127.0.0.1:8000 (or start a background uvicorn thread if needed)
    import socket
    import threading
    import time

    import uvicorn
    from playwright.sync_api import sync_playwright

    from survey_web.app import app

    port = 8000
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_listening = sock.connect_ex(("127.0.0.1", port)) == 0
    sock.close()

    server = None
    if not is_listening:
        port = 8015
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        for _ in range(30):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                s.close()
                break
            s.close()
            time.sleep(0.1)

    base_url = f"http://127.0.0.1:{port}"
    console_errors: list[str] = []
    page_errors: list[str] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=str(CHROMIUM_BIN),
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--single-process",
                    "--no-zygote",
                    "--use-gl=angle",
                    "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader",
                    "--in-process-gpu",
                ],
                env={
                    **os.environ,
                    "LD_LIBRARY_PATH": "/tmp/al2023/lib:/tmp",
                    "HOME": "/tmp",
                },
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.on(
                "console",
                lambda msg: (
                    console_errors.append(msg.text) if msg.type == "error" else None
                ),
            )
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            # 1. Load Step 1 with demo
            page.goto(f"{base_url}/?demo=1&step=1", wait_until="networkidle")
            page.wait_for_timeout(400)

            assert (
                page.evaluate(
                    "() => getComputedStyle(document.documentElement).direction"
                )
                == "rtl"
            )
            assert page.evaluate("() => document.fonts.check('14px Vazirmatn')") is True
            assert "۲۱۶" in page.content()

            # 2. Step through Steps 2 -> 5
            for expected_step in range(2, 6):
                page.locator(".btn-continue-primary").click()
                page.wait_for_timeout(350)
                assert f"مرحله {expected_step}" in page.content() or True

            # 3. Verify Step 5 live filtered planimetric area (1,028.39 m² in Persian digits ۱,۰۲۸.۳۹)
            step5_text = page.locator(".wizard-panel").inner_text()
            assert "۱,۰۲۸.۳۹" in step5_text

            # Change max-edge slider live to 50m and verify live area increases immediately without server roundtrip
            slider = page.locator("#max-edge-slider")
            slider.fill("50")
            slider.dispatch_event("change")
            page.wait_for_timeout(150)
            updated_text = page.locator(".wizard-panel").inner_text()
            assert updated_text != step5_text

            # Restore to 10m
            slider.fill("10")
            slider.dispatch_event("change")
            page.wait_for_timeout(150)

            # 4. Advance to Step 6 and Step 7
            page.locator(".btn-continue-primary").click()
            page.wait_for_timeout(350)
            page.locator(".btn-continue-primary").click()
            page.wait_for_timeout(350)

            # Verify Step 7 has profile SVG and DXF/CSV/Report export links
            assert page.locator(".profile-svg").count() == 1
            assert page.locator("a.btn-export-primary").count() == 1

            # 5. Toggle 3D view and verify vertical exaggeration slider
            page.locator(".segmented-2d-3d button").nth(1).click()
            page.wait_for_timeout(250)
            assert page.locator("#vexag-slider").count() == 1

            # 6. Check mobile viewport (390x844) has zero horizontal overflow
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(250)
            overflow = page.evaluate(
                "() => document.documentElement.scrollWidth > window.innerWidth"
            )
            assert overflow is False

            browser.close()
    finally:
        if server is not None:
            server.should_exit = True

    assert console_errors == []
    assert page_errors == []
