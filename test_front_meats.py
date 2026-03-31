from playwright.sync_api import sync_playwright

def run_cuj(page):
    page.goto("http://localhost:5000")
    page.wait_for_timeout(2000)

    page.on("console", lambda msg: print(f"Browser console: {msg.type}: {msg.text}"))
    page.on("pageerror", lambda err: print(f"Browser error: {err}"))

    # Enter pin: 1234
    page.get_by_text("1").click()
    page.wait_for_timeout(200)
    page.get_by_text("2").click()
    page.wait_for_timeout(200)
    page.get_by_text("3").click()
    page.wait_for_timeout(200)
    page.get_by_text("4").click()
    page.wait_for_timeout(2000)

    # Click on "Meats" category
    page.get_by_text("Meats").click()
    page.wait_for_timeout(2000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
