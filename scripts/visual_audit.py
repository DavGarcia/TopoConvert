"""Playwright visual & functional audit across all 7 wizard steps and 6 viewports."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWPORTS = [
    {"name": "360x640", "width": 360, "height": 640, "tag": "360"},
    {"name": "390x844", "width": 390, "height": 844, "tag": "390"},
    {"name": "844x390", "width": 844, "height": 390, "tag": "844"},
    {"name": "768x1024", "width": 768, "height": 1024, "tag": "768"},
    {"name": "1024x768", "width": 1024, "height": 768, "tag": "1024"},
    {"name": "1440x900", "width": 1440, "height": 900, "tag": "1440"},
]

ARTIFACTS_DIR = Path("/home/user/TopoConvert/artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def run_audit() -> dict:
    results = {
        "console_errors": [],
        "page_errors": [],
        "failed_requests": [],
        "overflow_issues": [],
        "small_touch_targets": [],
        "blank_canvas_issues": [],
        "rtl_issues": [],
        "screenshots": [],
    }

    with sync_playwright() as p:
        for vp in VIEWPORTS:
            browser = p.chromium.launch(
                executable_path="/tmp/chromium",
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
                    "LD_LIBRARY_PATH": "/tmp/al2023/lib:/tmp",
                    "HOME": "/tmp",
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                },
            )
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                device_scale_factor=2 if vp["width"] < 768 else 1,
            )
            page = context.new_page()

            page.on(
                "console",
                lambda msg, v=vp["name"]: (
                    results["console_errors"].append({"vp": v, "text": msg.text})
                    if msg.type == "error"
                    else None
                ),
            )
            page.on(
                "pageerror",
                lambda err, v=vp["name"]: results["page_errors"].append(
                    {"vp": v, "err": str(err)}
                ),
            )
            page.on(
                "response",
                lambda res, v=vp["name"]: (
                    results["failed_requests"].append(
                        {"vp": v, "url": res.url, "status": res.status}
                    )
                    if res.status >= 400
                    else None
                ),
            )

            # Open step 1 with demo auto-loaded
            page.goto("http://127.0.0.1:8000/?demo=1&step=1", wait_until="networkidle")
            page.wait_for_timeout(450)

            for step in range(1, 8):
                if step > 1:
                    cont_btn = page.locator(".btn-continue-primary")
                    cont_btn.click()
                    page.wait_for_timeout(450)

                page.evaluate("() => document.fonts.ready")
                page.wait_for_timeout(200)

                rtl_check = page.evaluate("""() => {
                        const dir = getComputedStyle(document.documentElement).direction;
                        const fontLoaded = document.fonts.check('14px Vazirmatn');
                        const scrollW = document.documentElement.scrollWidth;
                        const innerW = window.innerWidth;
                        return { dir, fontLoaded, scrollW, innerW };
                    }""")
                if rtl_check["dir"] != "rtl" or not rtl_check["fontLoaded"]:
                    results["rtl_issues"].append(
                        {"vp": vp["name"], "step": step, **rtl_check}
                    )
                if rtl_check["scrollW"] > rtl_check["innerW"] + 1:
                    results["overflow_issues"].append(
                        {"vp": vp["name"], "step": step, **rtl_check}
                    )

                canvas_check = page.evaluate("""() => {
                        const c = document.querySelector('.topo-canvas-2d');
                        if (!c) return { ok: false, reason: 'no_canvas' };
                        const ctx = c.getContext('2d');
                        if (!ctx || c.width === 0 || c.height === 0) return { ok: false, reason: 'zero_size' };
                        const data = ctx.getImageData(0, 0, c.width, c.height).data;
                        let nonBg = 0;
                        const r0 = data[0], g0 = data[1], b0 = data[2];
                        for (let i = 0; i < data.length; i += 16) {
                            if (Math.abs(data[i] - r0) + Math.abs(data[i+1] - g0) + Math.abs(data[i+2] - b0) > 15) {
                                nonBg++;
                            }
                        }
                        return { ok: nonBg > 20, nonBg, width: c.width, height: c.height };
                    }""")
                if not canvas_check.get("ok"):
                    results["blank_canvas_issues"].append(
                        {"vp": vp["name"], "step": step, **canvas_check}
                    )

                small_targets = page.evaluate("""() => {
                        const els = Array.from(document.querySelectorAll('button, select, a.btn-export-primary, a.btn-export-secondary'));
                        const bad = [];
                        for (const el of els) {
                            const style = getComputedStyle(el);
                            if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) continue;
                            const r = el.getBoundingClientRect();
                            if (r.width === 0 && r.height === 0) continue;
                            if (r.height < 42 || r.width < 42) {
                                bad.push({
                                    tag: el.tagName,
                                    cls: el.className,
                                    text: (el.textContent || '').trim().slice(0, 25),
                                    w: Math.round(r.width),
                                    h: Math.round(r.height)
                                });
                            }
                        }
                        return bad;
                    }""")
                if small_targets:
                    results["small_touch_targets"].append(
                        {"vp": vp["name"], "step": step, "targets": small_targets}
                    )

                shot_path = ARTIFACTS_DIR / f"step_{step}_{vp['tag']}.png"
                page.screenshot(path=str(shot_path), full_page=False)
                results["screenshots"].append(str(shot_path))

            browser.close()

    return results


if __name__ == "__main__":
    summary = run_audit()
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k != "screenshots"},
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"Total screenshots saved: {len(summary['screenshots'])}")
