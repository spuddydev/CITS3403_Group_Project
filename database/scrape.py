from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent

ua = UserAgent()

def get_site_content(site_url) -> str:
    html = ""
    with sync_playwright() as p:

        # Launch a new browser with a fake user agent
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=ua.random)

        # Go to the url
        page = context.new_page()
        page.goto(site_url, timeout=6000)
        
        # Wait for the content to appear
        page.wait_for_selector("body", timeout=6000)
        
        # Save the HTML content
        html = page.content()
        browser.close()
    return html