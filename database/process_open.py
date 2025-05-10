from bs4 import BeautifulSoup
from datetime import datetime

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
        
    supervisors = []
    for supervisor in data.get("Supervisor", []):
        supervisor = supervisor.split(' ')
        supervisors.append({"first_name": supervisor[1], 
                            "last_name": supervisor[2],
                            "email": '.'.join(supervisor[1:]) + "@uwa.edu.au"
        })

    date = data.get('Close date', [None])[0]
    if date: 
        date = datetime.strptime(date, "%d %b %Y")

    # Flatten single-item lists to strings
    result = {
        'is_open': True,
        'title': data.get('Title', [None])[0],
        'link': link,
        'close_date': date,
        'supervisors':  supervisors,
        'research_areas': data.get('Research area', []),
        'summary': ' '.join(data.get('Project description', []))
    }

    return result

def get_all_open_projects(project_directory_link: str) -> list[dict]:
    projects = []
    for link in get_all_open_links(project_directory_link):
        info = get_project_info(link)
        if info.get("title") is not None:
            projects.append(info)
    return projects

if __name__ == "__main__":
    for project in get_all_open_projects("https://researchdegrees.uwa.edu.au/projects"):
        print(project)