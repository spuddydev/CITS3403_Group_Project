import feedparser
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent

ua = UserAgent()

def get_extra_details(repository_url: str) -> tuple[list, list]:

    # UWA has Cloudflare limiting, employ a headless browser to bypass
    # Note that as according to the UWA robots.txt I am allowed to 
    # scrape site information as I am not using it for disallowed topics

    html = ""
    with sync_playwright() as p:

        # Launch a new browser with a fake user agent
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=ua.random)

        # Go to the url
        page = context.new_page()
        page.goto(repository_url, timeout=6000)
        
        # Wait for the content to appear
        page.wait_for_selector("body", timeout=6000)
        
        # Save the HTML content
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, 'html.parser')

    # Find the ul by class containing all authors
    ul = soup.find('ul', class_='relations persons')

    # Loop through all li tags in the ul
    authors = []
    for li in ul.find_all('li'):
        # If there's an a tag, get text from span inside it
        a_tag = li.find('a')
        if a_tag:
            authors.append(a_tag.get_text(strip=True))
        else:
            # Else, get the text from the li directly, excluding the dimmed span
            full_text = li.get_text(separator=' ', strip=True)
            dimmed = li.find('span', class_='dimmed')
            if dimmed:
                dimmed_text = dimmed.get_text(strip=True)
                full_text = full_text.replace(dimmed_text, '').strip()
            authors.append(full_text)

    faculties = []

    # Find all relations organisations elements (faculties)
    ul_orgs = soup.find('ul', class_='relations organisations')
    if ul_orgs:
        for li in ul_orgs.find_all('li'):
            a_tag = li.find('a')
            if a_tag:
                faculties.append(a_tag.get_text(strip=True))
    
    return authors, faculties


def parse_rss_page_info(feed_url: str) -> list[dict]:

    # grab the rss feed
    feed = feedparser.parse(feed_url)
    results = []

    # Go through each entry
    entries = feed.entries
    for entry in entries:
        # Get the link title and publishing
        link = entry.get("link", "")
        title = entry.get("title", "")
        published = entry.get("published", "")
        
        if link:
            # grab the authors and faculty/faculties from the HTML
            authors, faculties = get_extra_details(link)

            # Ensure the page has rendered properly. Do not always have faculties
            if authors and title and published: 
                results.append({
                    "title": title,
                    "link": link,
                    "published": published, 
                    "authors": authors,
                    "faculties": faculties
                })

    return results


if __name__ == "__main__":
    feed_url = 'https://research-repository.uwa.edu.au/en/projects/?format=rss'
    parsed_entries = parse_rss_page_info(feed_url)

    print(len(parsed_entries))

