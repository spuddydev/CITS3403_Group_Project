import time
import random
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page
from fake_useragent import UserAgent
import requests
from xml.etree import ElementTree as ET

ua = UserAgent()

def get_closed_site_details(page: Page, url: str) -> dict:

    # UWA has Cloudflare limiting, employ a headless browser to bypass
    # Note that as according to the UWA robots.txt I am allowed to 
    # scrape site information as I am not using it for disallowed topics
    time.sleep(random.uniform(1.2, 4))
    page.goto(url)
    page.wait_for_selector("body", timeout=6000)
    html = page.content()

    soup = BeautifulSoup(html, 'html.parser')

    # Find title
    title = soup.find('div', class_='rendering').find('span').get_text(strip=True)

    p = soup.find('p', class_='relations persons')

    researchers = []

    # Extract all text segments and tags
    for item in p.contents:
        if isinstance(item, str):
            # Handle unlinked names (may contain multiple, split by commas)
            parts = [part.strip() for part in item.split(',') if part.strip()]
            for name in parts:
                if " " in name:
                    first_name, last_name = name.split(" ", 1)
                    first_name = first_name.replace(".", "").strip()
                    researchers.append({
                        "first_name": first_name,
                        "last_name": last_name
                    })
        elif item.name == 'a':
            name = item.get_text(strip=True)
            if " " in name:
                first_name, last_name = name.split(" ", 1)
                first_name = first_name.replace(".", "").strip()
                researcher_entry = {
                    "first_name": first_name,
                    "last_name": last_name,
                }
                if len(first_name) > 1:
                    researcher_entry["email"] = f"{first_name.lower()}.{last_name.lower().replace("'", "").replace(" ", "")}@uwa.edu.au"
                researchers.append(researcher_entry)

    research_areas = []

    # Find all relations organisations elements (faculties)
    ul_orgs = soup.find('ul', class_='relations organisations')
    if ul_orgs:
        for li in ul_orgs.find_all('li'):
            a_tag = li.find('a')
            if a_tag:
                research_areas.append(a_tag.get_text(strip=True))

    # Assuming `html` contains the entire HTML content

    abstract = None

    # Find the specific abstract container by all its unique classes
    abstract_container = soup.find('div', class_='rendering_researchoutput_abstractportal')
    if abstract_container:
        abstract_block = abstract_container.find('div', class_='textblock')
        if abstract_block:
            abstract_text = abstract_block.get_text(strip=True)
            abstract = abstract_text

    entry = {
            "title": title,
            "link": url,
            "is_open": False,
            "summary": abstract,
            "researcher": researchers,
            "research_areas": research_areas, 
        }
    
    return entry

def fetch_research_repo_urls(num_of_sitemaps: int, starting_number: int = 0):
    # Seemingly super strict on UA so had to play around and find this one
    headers = {
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
    }
    for i in range(starting_number, num_of_sitemaps):
 
        response = requests.get(f"https://research-repository.uwa.edu.au/sitemap/publications.xml?n={i+1}", headers=headers)
        response.raise_for_status()

        root = ET.fromstring(response.text)

        # Namespace handling (sitemaps often use a default namespace)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        for url in root.findall('ns:url', ns):
            loc = url.find('ns:loc', ns)
            if loc is not None and loc.text:
                yield loc.text

def fetch_closed_research(num_of_sitemaps: int = 1, starting_number: int = 0):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=ua.random)
        page = context.new_page()
        for url in fetch_research_repo_urls(num_of_sitemaps, starting_number):
            entry = get_closed_site_details(page, url)
            #print(entry) #DEBUG
            yield entry
        browser.close()
            