"""링커리어 디자인 파싱 스크립트."""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0",
        viewport={"width": 1440, "height": 900},
    )
    page = ctx.new_page()
    page.goto("https://linkareer.com/list/intern", timeout=30000, wait_until="networkidle")
    page.wait_for_timeout(2000)

    row_info = page.evaluate("""() => {
        const rows = document.querySelectorAll('tr[class*=ActivityTableRow]');
        if (!rows.length) return {rows: 0, html: ''};
        const row = rows[0];
        const styles = {};
        row.querySelectorAll('*').forEach(el => {
            const s = getComputedStyle(el);
            const cn = typeof el.className === 'string' ? el.className : '';
            const key = cn ? cn.substring(0,40) : el.tagName;
            styles[key] = {
                bg: s.backgroundColor,
                color: s.color,
                fontSize: s.fontSize,
                fontWeight: s.fontWeight,
                borderRadius: s.borderRadius,
            };
        });
        return {
            rows: rows.length,
            html: row.outerHTML.substring(0, 3000),
            styles: styles
        };
    }""")

    theme = page.evaluate("""() => {
        const found = new Set();
        document.querySelectorAll('*').forEach(el => {
            const s = getComputedStyle(el);
            ['backgroundColor','color'].forEach(p => {
                const v = s[p];
                if (v && v !== 'rgba(0, 0, 0, 0)' && v !== 'rgb(0, 0, 0)' && v !== 'rgba(0,0,0,0)') {
                    found.add(v);
                }
            });
        });
        return Array.from(found).slice(0, 40);
    }""")

    # 스크린샷
    page.screenshot(path="C:/tmp/linkareer.png")

    browser.close()

print(f"테이블 행 수: {row_info.get('rows', 0)}")
print()
print("=== 행 HTML ===")
print(row_info.get("html", "")[:2500])
print()
print("=== 색상 팔레트 ===")
for c in theme:
    print(f"  {c}")
