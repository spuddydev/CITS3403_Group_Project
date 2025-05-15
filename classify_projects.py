from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from database.schema import db, Project, Interest
from umap import UMAP
import re
from hdbscan import HDBSCAN
from app import app
from collections import defaultdict
from bertopic.representation import KeyBERTInspired
from bertopic.representation import MaximalMarginalRelevance
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction import _stop_words

NUMBER_OF_INTERESTS_FROM_TOPIC = 3
STOPWORDS = _stop_words.ENGLISH_STOP_WORDS

def clean_summary(text: str) -> str:
    text = re.sub(r"[^\w\s]", "", text)  # removes punctuation
    words = text.lower().split()
    return " ".join([
        w for w in words
        if w not in STOPWORDS and len(w) > 2 and not w.isnumeric()
    ])

with app.app_context():
    # Get all the summaries to classify
    projects = Project.query.all()
    summaries = [clean_summary(p.summary) for p in projects]

    # Define Vectoriser Model
    vectorizer_model = CountVectorizer(
        stop_words="english",
        ngram_range=(1, 2), 
        min_df=3,
        max_df=0.9               
    )

    # Embed summaries
    embedding_model = SentenceTransformer('thenlper/gte-small')
    embeddings = embedding_model.encode(summaries, show_progress_bar=True)
    print(embeddings.shape)

    # Reduce dimensionality of vectors (Like 348 (i think??) to 13)
    umap_model = UMAP(
        n_components=13, min_dist=0.0, metric='cosine', random_state=42
    )

    # Define the clustering model
    hdbscan_model = HDBSCAN(
        min_cluster_size=5,
        min_samples=3,
        metric='euclidean',
        cluster_selection_method='eom',
        prediction_data=True,
    )

    # Now training topic representation model 
    # Which uses c-TF-IDF to get a weighted bag of words
    # which topics can be taken off of! 
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        verbose=True
    ).fit(summaries, embeddings)

    
    print("First topics:")
    print(topic_model.get_topic_info())


    # Now we are honing (fine-tuning) the topics
    topic_model.update_topics(summaries, representation_model=KeyBERTInspired())
    # And then running a diversification algorithm to ensure that there are fewer,
    # More relevant topics for each cluster
    topic_model.update_topics(summaries, representation_model=MaximalMarginalRelevance(diversity=0.5))


    print("Final topics:")
    print(topic_model.get_topic_info())

    # Get raw topic assignments and probabilities
    tmp_topics, probs = topic_model.transform(summaries, embeddings=embeddings)

    # Apply reduce_outliers to remove -1s
    print(f"[DEBUG] Running reduce_outliers on {len(tmp_topics)} topics")
    topics = topic_model.reduce_outliers(
        documents=summaries,
        topics=tmp_topics,
        probabilities=probs,
        embeddings=embeddings,
        threshold=0.0
    )
    topic_model.update_topics(summaries,topics=topics)

    topic_model.save("models/interest_model_v1")

    # Extract top N keywords per topic
    topic_keywords = defaultdict(list)
    for topic_id in set(topics):
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
