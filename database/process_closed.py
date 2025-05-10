import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
try:
    from database.scrape import get_site_content
except ModuleNotFoundError:
    from scrape import get_site_content

def get_extra_details(repository_url: str) -> tuple[list, list]:

    # UWA has Cloudflare limiting, employ a headless browser to bypass
    # Note that as according to the UWA robots.txt I am allowed to 
    # scrape site information as I am not using it for disallowed topics

    html = get_site_content(repository_url)

    soup = BeautifulSoup(html, 'html.parser')

    # Find the ul by class containing all authors
    ul = soup.find('ul', class_='relations persons')

    # Loop through all li tags in the ul
    supervisors = []
    for li in ul.find_all('li'):
        # If there's an a tag, get text from span inside it
        a_tag = li.find('a')
        if a_tag:
            name = a_tag.get_text(strip=True)
            # Put the name in order firstname lastname and add an email address when they are staff at uwa
            name = name.split(', ')[::-1]
            first_name = name[0]
            last_name = name[1]
            supervisors.append({"first_name": first_name,
                                "last_name": last_name,
                                "email": ".".join(name) + "@uwa.edu.au"})
        else:
            # Else, get the text from the li directly, excluding the dimmed span
            full_text = li.get_text(separator=' ', strip=True)
            dimmed = li.find('span', class_='dimmed')
            if dimmed:
                dimmed_text = dimmed.get_text(strip=True)
                full_text = full_text.replace(dimmed_text, '').strip()
            name = full_text.split(', ')[::-1]
            first_name = name[0]
            last_name = name[1]
            supervisors.append({"first_name": first_name,
                                "last_name": last_name})

    research_areas = []

    # Find all relations organisations elements (faculties)
    ul_orgs = soup.find('ul', class_='relations organisations')
    if ul_orgs:
        for li in ul_orgs.find_all('li'):
            a_tag = li.find('a')
            if a_tag:
                research_areas.append(a_tag.get_text(strip=True))
    
    return supervisors, research_areas


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
            supervisors, research_areas = get_extra_details(link)

            # Ensure the page has rendered properly. Do not always have faculties
            if supervisors and title and published: 
                entry = {
                    "is_open": False,
                    "title": title,
                    "link": link,
                    "publication_date": datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z"), 
                    "supervisors": supervisors,
                    "research_areas": research_areas
                }
                results.append(entry)
    
    return results


if __name__ == "__main__":
    feed_url = 'https://research-repository.uwa.edu.au/en/projects/?format=rss'
    parsed_entries = parse_rss_page_info(feed_url)

    print(len(parsed_entries))

