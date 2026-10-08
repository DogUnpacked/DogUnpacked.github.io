#!/usr/bin/env python3
"""Render review screenshots of the hub page with Playwright Chromium.

Outputs (gitignored, local review only; mobile shots are quantized to 256 colors if Pillow is available):
  assets/preview-v2-desktop.png       1280 wide, full page
  assets/preview-v2-mobile.png        375 wide, full page
  assets/preview-v2-mobile-dobie.png  375 wide, ?breed=dobie
  assets/preview-v2-mobile-pitbull.png 375 wide, ?breed=pit-bull

Serves the folder over a local HTTP server (so ?breed= works) and prints layout checks.
"""
import asyncio, functools, http.server, pathlib, socketserver, threading
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 0  # 0 = any free port

CHECK_JS = """() => {
  const r = el => el && el.getBoundingClientRect();
  const submit = document.querySelector('#newsletter-form button[type="submit"]');
  const box = submit && r(submit);
  const small = [...document.querySelectorAll('a.social-btn, button, a.btn, a.nav-cta, input, select')]
    .filter(e => e.offsetParent && e.id !== 'contact-website' && r(e).height < 44)
    .map(e => e.outerHTML.slice(0, 60));
  return {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    submitBottom: box && Math.round(box.bottom),
    heading: document.getElementById('newsletter-heading').textContent,
    kicker: document.getElementById('hero-kicker').textContent,
    breedValue: document.getElementById('breed').value,
    stat: document.getElementById('breed-stat-text').textContent,
    latestVisible: !document.getElementById('latest').hidden,
    latestEmbed: !!document.querySelector('#latest-video .lite-yt-btn img'),
    latestCards: document.querySelectorAll('#latest-more a').length,
    footerTag: document.querySelector('.footer-tag').innerText,
    emailInHtml: /[A-Z0-9._%+\\-]+@[A-Z0-9.\\-]+\\.[A-Z]{2,}/i.test(document.documentElement.innerHTML),
    under44: small,
  };
}"""


def quantize(path):
    """Shrink a 2x screenshot (~2 MB -> ~0.8 MB). Skipped if Pillow isn't installed."""
    try:
        from PIL import Image
    except ImportError:
        return
    Image.open(path).convert("RGB").quantize(colors=256).save(path, optimize=True)


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
        ("preview-v2-mobile-pitbull", 375, 812, 2, "?breed=pit-bull"),
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
            if dpr > 1:
                quantize(ROOT / "assets" / f"{name}.png")
        await b.close()
    httpd.shutdown()


asyncio.run(main())
