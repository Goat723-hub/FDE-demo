# -*- coding: utf-8 -*-
"""
录一段真实操作：上传 -> 扫描 -> 改字段 -> 提交 -> 报价结果 -> 下载。

Playwright 的录屏不含鼠标指针，所以往页面里注入一个假指针和点击波纹，
录完用 ffmpeg 转成 GIF（README 用）和 MP4（完整画质）。
"""

import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"
RAW = ROOT / "screenshots" / "_raw"
URL = "http://127.0.0.1:8000/"

CURSOR_JS = """
(() => {
  const style = document.createElement('style');
  style.textContent = `
    #__cursor {
      position: fixed; left: 0; top: 0; width: 28px; height: 28px;
      z-index: 2147483647; pointer-events: none;
      transform: translate(-80px, -80px);
      transition: transform 0.4s cubic-bezier(.33,0,.2,1);
    }
    #__cursor svg { filter: drop-shadow(0 2px 3px rgba(0,0,0,.35)); }
    .__ripple {
      position: fixed; width: 12px; height: 12px; margin: -6px 0 0 -6px;
      border: 2px solid #C2410C; border-radius: 50%; z-index: 2147483646;
      pointer-events: none; animation: __rip .55s ease-out forwards;
    }
    @keyframes __rip {
      to { width: 54px; height: 54px; margin: -27px 0 0 -27px; opacity: 0; }
    }
  `;
  document.head.appendChild(style);

  const cur = document.createElement('div');
  cur.id = '__cursor';
  cur.innerHTML = '<svg viewBox="0 0 24 24" width="28" height="28">'
    + '<path d="M4 2 L4 19 L9 14.5 L12.5 22 L15.5 20.5 L12 13 L18.5 12.5 Z" '
    + 'fill="#1A1A1A" stroke="#FFFDF8" stroke-width="1.4"/></svg>';
  document.body.appendChild(cur);

  window.__moveCursor = (x, y) => {
    cur.style.transform = `translate(${x}px, ${y}px)`;
  };
  window.__hideCursor = () => { cur.style.display = 'none'; };

  document.addEventListener('mousedown', (e) => {
    const r = document.createElement('div');
    r.className = '__ripple';
    r.style.left = e.clientX + 'px';
    r.style.top = e.clientY + 'px';
    document.body.appendChild(r);
    setTimeout(() => r.remove(), 650);
  }, true);
})();
"""


def center(box):
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def move(page, x, y, settle=0.45):
    page.evaluate("([x, y]) => window.__moveCursor(x, y)", [x, y])
    time.sleep(settle)


def click_at(page, x, y):
    page.mouse.click(x, y)
    time.sleep(0.35)


def main():
    OUT.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 950},
            record_video_dir=str(RAW),
            record_video_size={"width": 1440, "height": 950},
            accept_downloads=True,
        )
        page = context.new_page()
        page.goto(URL, wait_until="networkidle")
        page.evaluate(CURSOR_JS)
        time.sleep(0.8)

        # 01 把鼠标移到上传卡片并点击
        upload = page.locator(".upload-card")
        x, y = center(upload.bounding_box())
        move(page, x - 220, y + 160, settle=0.05)
        move(page, x, y, settle=0.7)
        click_at(page, x, y)

        # 02 扫描动画
        time.sleep(1.6)
        page.wait_for_selector(".item-card:not(.skeleton)", timeout=120_000)
        time.sleep(1.4)

        # 03 改一个字段：把第一个零件的交期从 7 改成 9
        delivery = page.locator(".item-card").nth(0).locator('input[type="number"]').nth(2)
        dx, dy = center(delivery.bounding_box())
        move(page, dx, dy)
        click_at(page, dx, dy)
        page.keyboard.press("Control+A")
        time.sleep(0.25)
        page.keyboard.type("9", delay=220)
        time.sleep(0.5)
        page.evaluate("document.activeElement && document.activeElement.blur()")
        time.sleep(0.4)

        # 04 提交
        confirm = page.get_by_role("button", name="确认并计价 →")
        cx, cy = center(confirm.bounding_box())
        move(page, cx, cy, settle=0.55)
        click_at(page, cx, cy)

        # 05 结果页：总价滚动 + 摘要逐字
        page.wait_for_selector(".result", timeout=120_000)
        time.sleep(3.8)

        # 06 下载 PDF
        download = page.get_by_role("button", name="下载 PDF 报价单 ↓")
        lx, ly = center(download.bounding_box())
        move(page, lx, ly, settle=0.6)
        try:
            with page.expect_download(timeout=20_000):
                page.mouse.click(lx, ly)
        except Exception:
            pass
        time.sleep(1.6)

        video_obj = page.video
        context.close()  # 关闭时才会把视频写盘
        video = video_obj.path()
        browser.close()

    print("webm:", video)
    convert(Path(video))


def convert(webm: Path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    gif = OUT / "demo.gif"
    mp4 = OUT / "demo.mp4"

    # GIF：10fps、900px 宽、96 色调色板，兼顾清晰度和体积
    subprocess.run(
        [
            ffmpeg, "-y", "-i", str(webm),
            "-vf",
            "fps=10,scale=900:-1:flags=lanczos,split[s0][s1];"
            "[s0]palettegen=max_colors=96[p];"
            "[s1][p]paletteuse=dither=bayer:bayer_scale=3",
            "-loop", "0", str(gif),
        ],
        check=True,
        capture_output=True,
    )

    # MP4：完整画质，README 里给链接
    subprocess.run(
        [
            ffmpeg, "-y", "-i", str(webm),
            "-vf", "scale=1280:-2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
            "-movflags", "+faststart", str(mp4),
        ],
        check=True,
        capture_output=True,
    )

    print(f"gif: {gif} ({gif.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"mp4: {mp4} ({mp4.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    sys.exit(main())
