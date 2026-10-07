#!/usr/bin/env python3
"""Render review screenshots of the hub page with Playwright Chromium.

Outputs (gitignored, local review only):
  assets/preview-v2-desktop.png       1280 wide, full page
  assets/preview-v2-mobile.png        375 wide, full page
  assets/preview-v2-mobile-dobie.png  375 wide, ?breed=dobie

Serves the folder over a local HTTP server (so ?breed= works) and prints layout checks.
"""
import asyncio, functools, http.server, pathlib, socketserver, threading
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 0  # 0 = any free port

CHECK_JS = """() => {
  const r = el => el && el.getBoundingClientRect();
  const overlap = (a, b) => a && b && !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
  const pit = document.querySelector('img[src*="pit-bull-480"]');
  const paw = document.querySelector('.paw-watermark--br');
  const chips = [...document.querySelectorAll('.deco-chip')].map(c => Math.round(r(c).top));
  const small = [...document.querySelectorAll('a.social-btn, button, a.btn, input')]
    .filter(e => e.offsetParent && r(e).height < 44).map(e => e.outerHTML.slice(0, 60));
  return {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    pitOverlapsPaw: overlap(pit && pit.offsetParent ? r(pit.closest('figure')) : null, r(paw)),
    chipTops: chips,
    heading: document.getElementById('newsletter-heading').textContent,
    breedValue: document.getElementById('breed').value,
    firstGuide: document.querySelector('#guide-list .guide-card').dataset.breed,
    under44: small,
  };
}"""


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    class Server(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = Server(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


async def main():
    httpd = serve()
    port = httpd.server_address[1]
    shots = [
        ("preview-v2-desktop", 1280, 900, 1, ""),
        ("preview-v2-mobile", 375, 812, 2, ""),
        ("preview-v2-mobile-dobie", 375, 812, 2, "?breed=dobie"),
    ]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, w, h, dpr, qs in shots:
            ctx = await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr)
            pg = await ctx.new_page()
            errors = []
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errors.append(str(e)))
            await pg.goto(f"http://127.0.0.1:{port}/index.html{qs}", wait_until="load")
            # Load lazy images: scroll through the page.
            height = await pg.evaluate("document.body.scrollHeight")
            for y in range(0, height, 400):
                await pg.evaluate(f"window.scrollTo(0,{y})")
                await pg.wait_for_timeout(60)
            await pg.evaluate("window.scrollTo(0,0)")
            await pg.wait_for_timeout(600)
            print(name, await pg.evaluate(CHECK_JS))
            print("  errors:", [e for e in errors if "goatcounter" not in e and "gc.zgo.at" not in e])
            await pg.screenshot(path=str(ROOT / "assets" / f"{name}.png"), full_page=True)
            await ctx.close()
        await b.close()
    httpd.shutdown()


asyncio.run(main())
