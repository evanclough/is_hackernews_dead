"""
    Various utilities for interaction with the Chroma database used
    to store embeddings of text data in the datasets.
"""

import chromadb

import utils

import functools
import uuid

"""
    For chroma errors
"""
class ChromaError(Exception):
    def __init__(self, message):
        super().__init__(message)

"""
    A class used to create the object with which the dataset
    will interact with Chroma

    (wanted to do this the same way i did sqlite with connection only being open when necessary,
    but looks like chroma doesnt have functionality for that. oh well.)
"""
class ChromaDB:
    def __init__(self, path, create=False):
        self.path = path
        self.client = chromadb.PersistentClient(path=self.path)
        self.embedding_function = chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
                api_key=utils.fetch_env_var("OPENAI_API_KEY"),
                model_name=utils.fetch_env_var("EMBEDDING_MODEL")
        )

        if create:
            self._create()

    """
        Create a chroma db at a given path, with collections for the three root datatypes.
    """
    def _create(self):

        self.client = chromadb.PersistentClient(path=self.path)

        self.client.create_collection(name="user_abouts", embedding_function=self.embedding_function)
        self.client.create_collection(name="user_text_samples", embedding_function=self.embedding_function)
        self.client.create_collection(name="user_beliefs", embedding_function=self.embedding_function)
        self.client.create_collection(name="user_interests", embedding_function=self.embedding_function)

        self.client.create_collection(name="post_titles", embedding_function=self.embedding_function)
        self.client.create_collection(name="post_text_contents", embedding_function=self.embedding_function)
        self.client.create_collection(name="post_url_contents", embedding_function=self.embedding_function)

        self.client.create_collection(name="comment_text_contents", embedding_function=self.embedding_function)
    

    """
        Generate embeddings for a list of user profiles and add them to the database.
        Using random ids for the list attributes as I'll access them with metadata queries
    """
    def embed_user_profiles(self, user_profiles):
        user_abouts = self.client.get_collection(name="user_abouts")
        user_abouts.add(
            documents = [user_profile.about for user_profile in user_profiles if user_profile.about != ""],
            ids = [user_profile.username for user_profile in user_profiles if user_profile.about != ""]
        )

        filtered_for_text_samples = [user_profile for user_profile in user_profiles if len(user_profile.text_samples) > 0]
        if len(filtered_for_text_samples) > 0:
            user_text_samples = self.client.get_collection(name="user_text_samples", embedding_function=self.embedding_function)
            reduced_text_samples = functools.reduce(lambda acc, t: [*acc, *[{"text": te, "username": t.username, "id": uuid.uuid4()}for te in t.text_samples]], filtered_for_text_samples, [])
            user_text_samples.add(
                documents = [t["text"] for t in reduced_text_samples],
                metadatas= [{"username": t["username"]} for t in reduced_text_samples],
                ids = [str(t["id"]) for t in reduced_text_samples]
            )

        filtered_for_beliefs = [user_profile for user_profile in user_profiles if len(user_profile.beliefs) > 0]
        if len(filtered_for_beliefs) > 0:
            user_beliefs = self.client.get_collection(name="user_beliefs", embedding_function=self.embedding_function)
            reduced_beliefs = functools.reduce(lambda acc, t: [*acc, *[{"belief": te, "username": t.username, "id": uuid.uuid4()}for te in t.beliefs]], filtered_for_beliefs, [])
            user_beliefs.add(
                documents = [t["belief"] for t in reduced_beliefs],
                metadatas= [{"username": t["username"]} for t in reduced_beliefs],
                ids = [str(t["id"]) for t in reduced_beliefs]
            )

        filtered_for_interests = [user_profile for user_profile in user_profiles if len(user_profile.interests) > 0]
        if len(filtered_for_interests) > 0:
            user_interests = self.client.get_collection(name="user_interests", embedding_function=self.embedding_function)
            reduced_interests = functools.reduce(lambda acc, t: [*acc, *[{"interest": te, "username": t.username, "id": uuid.uuid4()}for te in t.interests]], filtered_for_interests, [])
            user_interests.add(
                documents = [t["belief"] for t in reduced_interests],
                metadatas= [{"username": t["username"]} for t in reduced_interests],
                ids = [str(t["id"]) for t in reduced_interests]
            )

    """
        Generate embeddings for a list of posts and add them to the database.
    """
    def embed_posts(self, posts):
        post_titles = self.client.get_collection(name="post_titles", embedding_function=self.embedding_function)
        post_titles.add(
            documents = [post.title for post in posts],
            ids = [str(post.id) for post in posts]
        )

        post_text_contents = self.client.get_collection(name="post_text_contents", embedding_function=self.embedding_function)
        post_text_contents.add(
            documents = [post.text for post in posts if post.text != ""],
            ids = [str(post.id) for post in posts if post.text != ""]
        )

        post_url_contents = self.client.get_collection(name="post_url_contents", embedding_function=self.embedding_function)
        post_url_contents = self.client.add(
            documents = [post.urlContent for post in posts if post.url_content != ""],
            metadatas = [{"url": post.url} for post in posts if post.url_content != ""],
            ids = [str(post.id) for post in posts if post.url_content != ""]
        )

    """
        Generate embeddings for a list of comments and add them to the database.
    """
    def embed_comments(self, comments):
        comment_text_contents = self.client.get_collection(name="comment_text_contents", embedding_function=self.embedding_function)
        comment_text_contents.add(
            documents = [comment.text for comment in comments],
            ids = [str(comment.id) for comment in comments]
        )