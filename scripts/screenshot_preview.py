#!/usr/bin/env python3
"""Render assets/preview-logo-{desktop,mobile}.png (1280 / 390 wide) with Playwright Chromium."""
import asyncio, sys
from playwright.async_api import async_playwright
import pathlib
ROOT=str(pathlib.Path(__file__).resolve().parent.parent)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        errors=[]
        for name,w,h,full in [('desktop',1280,900,True),('mobile',390,844,True)]:
            ctx=await b.new_context(viewport={'width':w,'height':h}, device_scale_factor=2 if name=='mobile' else 1)
            pg=await ctx.new_page()
            pg.on('console', lambda m: errors.append(m.text) if m.type=='error' else None)
            pg.on('requestfailed', lambda r: errors.append('FAILED '+r.url))
            await pg.goto(f'file://{ROOT}/index.html', wait_until='networkidle')
            await pg.wait_for_timeout(500)
            info=await pg.evaluate("""()=>{const i=document.querySelector('.hero-logo');const r=i.getBoundingClientRect();return {src:i.currentSrc,w:r.width,h:r.height,top:r.top,complete:i.complete,nw:i.naturalWidth, sw:document.documentElement.scrollWidth}}""")
            print(name, info)
            await pg.screenshot(path=f'{ROOT}/assets/preview-logo-{name}.png', full_page=full)
            await ctx.close()
        print('errors', errors)
        await b.close()
asyncio.run(main())
