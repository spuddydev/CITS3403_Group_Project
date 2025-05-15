from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from database.schema import db, Project, Interest
from umap import UMAP
from hdbscan import HDBSCAN
from app import app
from bertopic.representation import KeyBERTInspired
from bertopic.representation import MaximalMarginalRelevance
from collections import defaultdict

NUMBER_OF_INTERESTS_FROM_TOPIC = 3

with app.app_context():
    # Get all the summaries to classify
    projects = Project.query.all()
    summaries = [p.summary for p in projects]

    # Embed summaries
    embedding_model = SentenceTransformer('thenlper/gte-small')
    embeddings = embedding_model.encode(summaries, show_progress_bar=True)
    print(embeddings.shape)

    # Reduce dimensionality of vectors (Like 2048 (i think??) to 5)
    umap_model = UMAP(
        n_components=5, min_dist=0.0, metric='cosine', random_state=42
    )

    # Define the clustering model
    hdbscan_model = HDBSCAN(
        min_cluster_size=50,
        metric='euclidean',
        cluster_selection_method='eom',
        prediction_data=True 
    )

    # Now training topic representation model 
    # Which uses c-TF-IDF to get a weighted bag of words
    # which topics can be taken off of! 
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        verbose=True
    ).fit(summaries, embeddings)
    topic_model.reduce_outliers(summaries, embeddings, threshold=0.0)

    print("First topics:")
    print(topic_model.get_topic_info())

    # Now we are honing (fine-tuning) the topics
    representation_model = KeyBERTInspired()
    topic_model.update_topics(summaries, representation_model=representation_model)

    # And then running a diversification algorithm to ensure that there are fewer,
    # More relevant topics for each cluster
    representation_model = MaximalMarginalRelevance(diversity=0.5)
    topic_model.update_topics(summaries, representation_model=representation_model)
    print("Final topics:")
    print(topic_model.get_topic_info())

    # Save model
    topic_model.save("models/interest_model_v1")

    # Assign topics to projects
    topics, _ = topic_model.transform(summaries)

    # Extract top N keywords per topic
    topic_keywords = defaultdict(list)
    for topic_id in set(topics):
        # There should be no outliers, but -1 is an outlier
        # So skip if there are
        if topic_id == -1:
            continue
        top_words = topic_model.get_topic(topic_id)[:NUMBER_OF_INTERESTS_FROM_TOPIC]
        for word, _ in top_words:
            topic_keywords[topic_id].append(word)

    # Create Interests in DB
    existing_interests = {i.interest_name: i for i in Interest.query.all()}
    for word_list in topic_keywords.values():
        for word in word_list:
            if word not in existing_interests:
                interest = Interest(interest_name=word)
                db.session.add(interest)
                existing_interests[word] = interest
    db.session.commit()

    # Link each project to its topic's interests
    for project, topic_id in zip(projects, topics):
        if topic_id == -1:
            continue
        print(f"Project: {project.title} - Interests: {', '.join(topic_keywords[topic_id])}")
        for word in topic_keywords[topic_id]:
            interest_obj = existing_interests[word]
            if interest_obj not in project.interests:
                project.interests.append(interest_obj)
    db.session.commit()
