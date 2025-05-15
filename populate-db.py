from database.schema import db, Project, ResearchArea, Researcher
from database.process_closed import fetch_closed_research
from database.process_open import fetch_all_open_projects
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from app import app

# Helper functions

def get_or_create_research_area(session, name):
    area = session.query(ResearchArea).filter_by(area=name).first()
    if not area:
        area = ResearchArea(area=name)
        session.add(area)
        session.flush()
    return area

def get_or_create_researcher(session, first_name, last_name, email=None):
    query = session.query(Researcher).filter_by(first_name=first_name, last_name=last_name)
    if email:
        query = query.filter_by(email=email)
    researcher = query.first()
    if not researcher:
        researcher = Researcher(first_name=first_name, last_name=last_name, email=email)
        session.add(researcher)
        session.flush()
    return researcher

def project_exists(session, title, link):
    return session.query(Project).filter_by(title=title, link=link).first()

def insert_project(session, entry):
    if project_exists(session, entry["title"], entry["link"]):
        return None  # Skip duplicate
    if not entry["is_open"]:
        project = Project(
            title=entry["title"],
            link=entry["link"],
            is_open=entry["is_open"],
            summary=entry["summary"],
        )
    else:
         project = Project(
            title=entry["title"],
            link=entry["link"],
            is_open=entry["is_open"],
            summary=entry["summary"],
            close_date=entry["close_date"]
        )
         
    session.add(project) 

    for res in entry.get("researcher", []):
        first = res.get("first_name")
        last = res.get("last_name")
        email = res.get("email")
        if first and last:
            researcher = get_or_create_researcher(session, first, last, email)
            project.researchers.append(researcher)

    for area in entry.get("research_areas", []):
        project.research_areas.append(get_or_create_research_area(session, area))

    return project

# Final insert function (pass a generator in to yield)
def insert_all_entries(generator, batch_size=100):
    Session = sessionmaker(bind=db.engine)
    session = Session()
    count = 0
    batch_count = 0

    for entry in generator:
        try:
            if entry.get("summary") is None or entry.get("title") is None or len(entry.get("researcher")) == 0:
                continue

            result = insert_project(session, entry)
            if result:
                batch_count += 1
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[ERROR] Skipped project due to: {e}")
            continue

        if batch_count >= batch_size:
            try:
                session.commit()
                print(f"[BATCH COMMIT] Inserted {batch_count} projects.")
                count += batch_count
                batch_count = 0
            except SQLAlchemyError as e:
                session.rollback()
                print(f"[COMMIT ERROR] Failed to commit batch: {e}")

    # Final commit
    if batch_count > 0:
        try:
            session.commit()
            print(f"[FINAL COMMIT] Inserted final {batch_count} projects.")
            count += batch_count
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[FINAL COMMIT ERROR] {e}")

    session.close()
    print(f"[DONE] Total inserted: {count}")

if __name__ == "__main__":
    with app.app_context():
        #insert_all_entries(fetch_closed_research(22, 2), batch_size=100)
        insert_all_entries(fetch_all_open_projects("https://researchdegrees.uwa.edu.au/projects"), batch_size=10)
