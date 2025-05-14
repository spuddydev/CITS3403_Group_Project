from database.process_closed import parse_rss_page_info
from database.process_open import get_all_open_projects
from database.schema import *
from app import app

def supervisor_exists(first_name: str, last_name: str) -> bool:
    return db.session.query(Supervisor).filter(
        (Supervisor.first_name == first_name) & (Supervisor.last_name == last_name)
    ).first() is not None

def project_exists(project_title: str) -> bool:
    return db.session.query(Project).filter_by(title=project_title).first() is not None

def research_area_exists(research_area: str) -> bool:
    return db.session.query(ResearchArea).filter_by(area=research_area).first() is not None

def sync_with_db(data:list[dict]) -> None:
    for entry in data:
        # Skip if project already exists
        if project_exists(entry["title"]):
            continue

        # Get or create Supervisor objects
        supervisor_objs = []
        for sup in entry["supervisors"]:
            if not supervisor_exists(sup["first_name"], sup["last_name"]):
                supervisor = Supervisor(
                    first_name=sup["first_name"],
                    last_name=sup["last_name"],
                    email=sup.get("email")
                )
                db.session.add(supervisor)
                supervisor_objs.append(supervisor)

        # Get or create ResearchArea objects
        research_area_objs = []
        for area in entry["research_areas"]:
            if not research_area_exists(area):
                ra = ResearchArea(area=area)
                db.session.add(ra)
                research_area_objs.append(ra)

        # Create and link the project
        project = Project(
            title=entry["title"],
            link=entry["link"],
            is_open=entry["is_open"],
            summary=entry.get("summary"),
            close_date=entry.get("close_date"),
            publication_date=entry.get("publication_date"),
            supervisors=supervisor_objs,
            research_area=research_area_objs
        )

        db.session.add(project)

    db.session.commit()
             


if __name__ == "__main__":
    with app.app_context():
        sync_with_db((parse_rss_page_info("https://research-repository.uwa.edu.au/en/projects/?format=rss") + get_all_open_projects("https://researchdegrees.uwa.edu.au/projects")))