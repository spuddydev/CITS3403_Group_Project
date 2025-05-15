from bs4 import BeautifulSoup
from datetime import datetime
from playwright.sync_api import sync_playwright, Page
import time
import random
from fake_useragent import UserAgent

ua = UserAgent()

def get_all_open_links(page: Page, url: str) -> list[str]:
    time.sleep(random.uniform(1.2, 4))
    page.goto(url)
    page.wait_for_selector("body", timeout=6000)
    html = page.content()

    soup = BeautifulSoup(html, 'html.parser')

    hrefs = []
    for media_div in soup.find_all('div', class_='media my-4'):
        a_tag = media_div.find('a', href=True)
        if a_tag:
            hrefs.append('/'.join(url.split('/')[:3]) + a_tag['href'])
    return hrefs

def get_project_info(page, url: str) -> dict:
    time.sleep(random.uniform(1.2, 4))
    page.goto(url)
    page.wait_for_selector("body", timeout=6000)
    html = page.content()

    soup = BeautifulSoup(html, 'html.parser')

    # Define a mapping of the labels to extract
    fields_to_extract = {'Title', 'Supervisor', 'Research area', 'Project description', 'Close date'}
    data = {}
    current_field = None

    for row in soup.select('table.haplo-object tr'):
        th = row.find('th')
        td = row.find('td')

        if not td:
            continue  # skip malformed rows

        if th and (label := th.get_text(strip=True)):
            if label in fields_to_extract:
                current_field = label
                value = td.get_text(separator=' ', strip=True)
                data[current_field] = [value]  # start new list
            else:
                current_field = None
        elif current_field:
            # append to existing list for repeated rows
            value = td.get_text(separator=' ', strip=True)
            data.setdefault(current_field, []).append(value)
        
    researchers = []
    for researcher in data.get("Supervisor", []):
        researcher = researcher.split(' ')
        researcher_entry = {"first_name": researcher[1], 
                            "last_name": researcher[2],
        }
        email = ('.'.join(researcher[1:]) + "@uwa.edu.au").replace("'", "").replace(" ", "")
        researcher_entry["email"] = email
        researchers.append(researcher_entry)

    date = data.get('Close date', [None])[0]
    if date: 
        date = datetime.strptime(date, "%d %b %Y")

    # Flatten single-item lists to strings
    result = {
        'is_open': True,
        'title': data.get('Title', [None])[0],
        'link': url,
        'close_date': date,
        'researchers':  researchers,
        'research_areas': data.get('Research area', []),
        'summary': ' '.join(data.get('Project description', []))
    }

    return result

def fetch_all_open_projects(project_directory_url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=ua.random)
        page = context.new_page()
        for link in get_all_open_links(page, project_directory_url):
            info = get_project_info(page, link)
            if info.get("title") is not None and info.get("close_date") is not None:
                yield info
        browser.close()

if __name__ == "__main__":
    for project in fetch_all_open_projects("https://researchdegrees.uwa.edu.au/projects"):
        print(project)
