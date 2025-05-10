from bs4 import BeautifulSoup
try:
    from database.scrape import get_site_content
except ModuleNotFoundError:
    from scrape import get_site_content

def get_all_open_links(link: str) -> list[str]:
    html = get_site_content(link)
    soup = BeautifulSoup(html, 'html.parser')

    hrefs = []
    for media_div in soup.find_all('div', class_='media my-4'):
        a_tag = media_div.find('a', href=True)
        if a_tag:
            hrefs.append('/'.join(link.split('/')[:3]) + a_tag['href'])
    return hrefs

def get_project_info(link: str) -> dict:
    html = get_site_content(link)
    soup = BeautifulSoup(html, 'html.parser')

    # Define a mapping of the labels to extract
    fields = {
        'Title': None,
        'Supervisor': None,
        'Research area': None,
        'Project description': None,
        'Close date': None
    }

    # Loop through all rows in the table and extract the desired fields
    for row in soup.select('table.haplo-object tr'):
        header = row.find('th')
        data = row.find('td')
        if header and data:
            label = header.get_text(strip=True)
            if label in fields:
                fields[label] = data.get_text(separator=' ', strip=True)

    # Rename for clarity
    result = {
        'title': fields['Title'],
        'supervisor': (" ".join(fields['Supervisor'].split(" ")[1:]), ".".join(fields['Supervisor'].split(" ")[1:]) + "@uwa.edu.au"),
        'research_area': fields['Research area'],
        'summary': fields['Project description'],
        'close_date': fields['Close date']
    }

    return result

def get_all_open_projects(project_directory_link: str) -> list[dict]:
    projects = []
    for link in get_all_open_links(project_directory_link):
        projects.append(get_project_info(link))
    return projects

if __name__ == "__main__":
    for project in get_all_open_projects("https://researchdegrees.uwa.edu.au/projects"):
        print(project)