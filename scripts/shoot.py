# -*- coding: utf-8 -*-
"""把完整流程跑一遍并截图（用本机已安装的 Edge）。"""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"
OUT.mkdir(exist_ok=True)

URL = "http://127.0.0.1:8000/"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 950},
            device_scale_factor=2,
            accept_downloads=True,
        )

        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(800)
        page.screenshot(path=OUT / "01-hero.png", full_page=True)
        print("shot 01 hero")

        page.click(".upload-card")
        page.wait_for_timeout(600)
        page.screenshot(path=OUT / "02-scanning.png")
        print("shot 02 scanning")

        page.wait_for_selector(".item-card:not(.skeleton)", timeout=120_000)
        page.wait_for_timeout(1600)
        page.screenshot(path=OUT / "03-review.png")
        print("shot 03 review")

        page.get_by_role("button", name="确认并计价 →").click()
        page.wait_for_selector(".result", timeout=120_000)
        page.wait_for_timeout(6000)
        page.screenshot(path=OUT / "04-result.png")
        print("shot 04 result")

        with page.expect_download() as info:
            page.get_by_role("button", name="下载 PDF 报价单 ↓").click()
        info.value.save_as(OUT / "quotation.pdf")
        print("saved pdf")

        browser.close()


if __name__ == "__main__":
    main()
