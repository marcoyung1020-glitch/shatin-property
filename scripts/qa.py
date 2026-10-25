from playwright.sync_api import sync_playwright
import os
exe=os.path.expanduser('~/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome')
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=exe)
    for tag,vp in (('d',{'width':1440,'height':900}),('m',{'width':375,'height':812})):
        pg=b.new_page(viewport=vp); errs=[]
        pg.on('console',lambda m: m.type=='error' and errs.append(m.text)); pg.on('pageerror',lambda e: errs.append(str(e)))
        pg.goto('http://localhost:8765/#listings'); pg.wait_for_timeout(1500)
        pg.select_option('#f-sort','pd'); pg.wait_for_timeout(500)
        pg.screenshot(path=f'/tmp/qa_{tag}_pd.png')
        print(tag, errs, pg.eval_on_selector_all('#tbl-list tbody tr td.c-first', 'e=>e.slice(0,4).map(x=>x.innerText)'))
        print(pg.evaluate('document.documentElement.scrollWidth'))
    b.close()
