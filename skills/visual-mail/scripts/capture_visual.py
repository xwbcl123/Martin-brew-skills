#!/usr/bin/env python3
"""
Capture a full-page screenshot of an HTML file using available headless browser tools.

Usage:
  python capture_visual.py <html_path> <output_png_path>

Tries in order:
  1. playwright CLI  (full-page, --full-page flag)
  2. Selenium + CDP  (Page.getLayoutMetrics + Page.captureScreenshot captureBeyondViewport)
  3. Selenium resize (JS scrollHeight + set_window_size -- less reliable, kept as fallback)
  4. chromium --screenshot (viewport only, last resort)

Exit codes:
  0  success
  1  all methods failed (prints blocker details to stderr)
"""

import sys
import base64
import subprocess
import shutil
import time
from pathlib import Path


def try_playwright(html_path: str, out_path: str) -> bool:
    if not shutil.which("playwright"):
        return False
    result = subprocess.run(
        ["playwright", "screenshot", "--full-page", f"file://{html_path}", out_path],
        capture_output=True, text=True, timeout=45,
    )
    return result.returncode == 0 and Path(out_path).exists()


def try_selenium_cdp(html_path: str, out_path: str) -> bool:
    """Full-page capture via Selenium + Chrome DevTools Protocol.

    Uses Page.getLayoutMetrics to get the exact content dimensions, then
    Page.captureScreenshot with captureBeyondViewport=True to capture the
    entire document regardless of viewport size. This avoids the browser-chrome
    height offset that makes set_window_size(scrollHeight) unreliable.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        return False

    chromedriver_path = shutil.which("chromedriver")
    if not chromedriver_path:
        return False

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1080,800")
    options.add_argument("--hide-scrollbars")

    driver = None
    try:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(f"file://{html_path}")
        # Allow CDN resources (Tailwind, Lucide, Google Fonts) to render
        time.sleep(3)

        # Get exact content dimensions via CDP
        metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
        content = metrics["contentSize"]
        c_width = content["width"]
        c_height = content["height"]

        # Override device metrics so the viewport covers the full content area.
        # This is required for captureBeyondViewport to work correctly.
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": int(c_width),
            "height": int(c_height),
            "deviceScaleFactor": 1,
            "mobile": False,
        })
        time.sleep(0.3)

        # Capture full document beyond viewport
        result = driver.execute_cdp_cmd("Page.captureScreenshot", {
            "format": "png",
            "captureBeyondViewport": True,
            "clip": {
                "x": 0,
                "y": 0,
                "width": c_width,
                "height": c_height,
                "scale": 1,
            },
        })

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(result["data"]))

        print(f"CDP metrics: contentSize={int(c_width)}x{int(c_height)}")
        return Path(out_path).exists()
    except Exception as e:
        print(f"Selenium CDP error: {e}", file=sys.stderr)
        return False
    finally:
        if driver:
            driver.quit()


def try_selenium_resize(html_path: str, out_path: str) -> bool:
    """Fallback: resize window to JS scrollHeight then save_screenshot.

    Less reliable than CDP because browser-chrome height offsets can cause
    the window to be slightly shorter than the full content.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        return False

    chromedriver_path = shutil.which("chromedriver")
    if not chromedriver_path:
        return False

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1080,800")
    options.add_argument("--hide-scrollbars")

    driver = None
    try:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(f"file://{html_path}")
        time.sleep(3)
        scroll_h = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
        )
        driver.set_window_size(1080, scroll_h)
        time.sleep(0.5)
        driver.save_screenshot(out_path)
        return Path(out_path).exists()
    except Exception as e:
        print(f"Selenium resize error: {e}", file=sys.stderr)
        return False
    finally:
        if driver:
            driver.quit()


def try_chromium_viewport(binary: str, html_path: str, out_path: str) -> bool:
    """Last-resort viewport-only capture. Content below 800px will be clipped."""
    if not shutil.which(binary):
        return False
    result = subprocess.run(
        [binary, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         f"--screenshot={out_path}", "--window-size=1080,800", f"file://{html_path}"],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0 and Path(out_path).exists()


def verify_footer(out_path: str, crop_path: str | None = None) -> str:
    """Crop the bottom 120px of the PNG and return a size+crop summary.

    Saves bottom crop to crop_path if provided (for visual inspection).
    Returns a one-line summary string.
    """
    try:
        from PIL import Image
        img = Image.open(out_path)
        w, h = img.size
        crop_h = min(120, h)
        bottom = img.crop((0, h - crop_h, w, h))
        if crop_path:
            bottom.save(crop_path)
        return f"{w}x{h} px; bottom {crop_h}px crop saved to {crop_path}"
    except Exception as e:
        return f"verification error: {e}"


def main():
    if len(sys.argv) not in (3, 4):
        print("Usage: capture_visual.py <html_path> <output_png_path> [bottom_crop_path]",
              file=sys.stderr)
        sys.exit(1)

    html_path = str(Path(sys.argv[1]).resolve())
    out_path = sys.argv[2]
    crop_path = sys.argv[3] if len(sys.argv) == 4 else None

    method = None

    if try_playwright(html_path, out_path):
        method = "playwright -- full-page"
    elif try_selenium_cdp(html_path, out_path):
        method = "selenium+CDP -- full-page (captureBeyondViewport)"
    elif try_selenium_resize(html_path, out_path):
        method = "selenium+chromedriver -- resize (may clip footer)"
    else:
        for binary in ["chromium-browser", "google-chrome", "chromium"]:
            if try_chromium_viewport(binary, html_path, out_path):
                method = f"{binary} -- VIEWPORT ONLY, content clipped"
                break

    if method is None:
        print(
            "ERROR: No screenshot tool available.\n"
            "Tried: playwright, selenium+CDP, selenium+resize, chromium-browser.",
            file=sys.stderr,
        )
        sys.exit(1)

    summary = verify_footer(out_path, crop_path)
    print(f"Screenshot saved: {out_path} ({method})")
    print(f"Verification: {summary}")
    sys.exit(0)


if __name__ == "__main__":
    main()
