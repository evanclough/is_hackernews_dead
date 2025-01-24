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
        self.client.create_collection(name="user_abouts", embedding_function=self.embedding_function)
        self.client.create_collection(name="user_text_samples", embedding_function=self.embedding_function)
        self.client.create_collection(name="user_beliefs", embedding_function=self.embedding_function)
        self.client.create_collection(name="user_interests", embedding_function=self.embedding_function)

        self.client.create_collection(name="post_titles", embedding_function=self.embedding_function)
        self.client.create_collection(name="post_text_contents", embedding_function=self.embedding_function)
        self.client.create_collection(name="post_url_contents", embedding_function=self.embedding_function)

        self.client.create_collection(name="comment_text_contents", embedding_function=self.embedding_function)
    
    """
        Get a collection of a given name.
    """
    def get_collection(self, name):
        return self.client.get_collection(name=name, embedding_function=self.embedding_function)

    """
        Create embeddings for a given collection, with given input
    """
    def create_embeddings(self, collection_name, documents, ids, metadatas=None):
        if len(documents) != len(ids):
            raise ChromaError("Error creating embeddings: provided list of documents differs in length from list of ids.")
        if metadatas != None:
            if len(metadatas) != len(ids):
                raise ChromaError("Error creating embeddings: provided list of metadata differs in length from documents and ids.")

        collection = self.get_collection(name=collection_name)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    """
        Generate embeddings for a list of user profiles and add them to the database.
        Using random ids for the list attributes as I'll access them with metadata queries
    """
    def embed_user_profiles(self, user_profiles):
        filtered_for_about = [user_profile for user_profile in user_profiles if user_profile.about != ""]
        about_documents = [user_profile.about for user_profile in filtered_for_about]
        about_ids = [user_profile.username for user_profile in filtered_for_about]
        self.create_embeddings("user_abouts", about_documents, about_ids)

        filtered_for_text_samples = [user_profile for user_profile in user_profiles if len(user_profile.text_samples) > 0]
        if len(filtered_for_text_samples) > 0:
            flattened_text_samples = functools.reduce(lambda acc, t: [*acc, *[{"text": te, "username": t.username, "id": uuid.uuid4()}for te in t.text_samples]], filtered_for_text_samples, [])
            text_sample_documents = [t["text"] for t in flattened_text_samples]
            text_sample_ids = [str(uuid.uuid4()) for t in flattened_text_samples]
            text_sample_metadatas = [{"username": t["username"]} for t in flattened_text_samples]
            self.create_embeddings("user_text_samples", text_sample_documents, text_sample_ids, metadatas=text_sample_metadatas)

        filtered_for_beliefs = [user_profile for user_profile in user_profiles if len(user_profile.beliefs) > 0]
        if len(filtered_for_beliefs) > 0:
            flattened_beliefs = functools.reduce(lambda acc, t: [*acc, *[{"belief": te, "username": t.username, "id": uuid.uuid4()}for te in t.beliefs]], filtered_for_beliefs, [])
            belief_documents = [t["belief"] for t in flattened_beliefs]
            belief_ids = [str(uuid.uuid4()) for t in flattened_beliefs]
            belief_metadatas = [{"username": t["username"]} for t in flattened_beliefs]
            self.create_embeddings("user_beliefs", belief_documents, belief_ids, metadatas=belief_metadatas)

        filtered_for_interests = [user_profile for user_profile in user_profiles if len(user_profile.interests) > 0]
        if len(filtered_for_interests) > 0:
            flattened_interests = functools.reduce(lambda acc, t: [*acc, *[{"interest": te, "username": t.username, "id": uuid.uuid4()}for te in t.interests]], filtered_for_interests, [])
            interest_documents = [t["interest"] for t in flattened_interests]
            interest_ids = [str(uuid.uuid4()) for t in flattened_interests]
            interest_metadatas = [{"username": t["username"]} for t in flattened_interests]
            self.create_embeddings("user_interests", interest_documents, interest_ids, metadatas=interest_metadatas)

    """
        Generate embeddings for a list of posts and add them to the database.
    """
    def embed_posts(self, posts):
        title_documents = [post.title for post in posts]
        title_ids = [str(post.id) for post in posts]
        self.create_embeddings("post_titles", title_documents, title_ids)

        filtered_for_text = [post for post in posts if post.text != ""]
        text_documents = [post.text for post in filtered_for_text]
        text_ids = [str(post.id) for post in filtered_for_text]
        self.create_embeddings("post_text_contents", text_documents, text_ids)

        filtered_for_url = [post for post in posts if post.url_content != ""]
        url_documents = [post.url_content for post in filtered_for_url]
        url_ids = [str(post.id) for post in filtered_for_url]
        url_metadatas = [{"url": post.url} for post in filtered_for_url]
        self.create_embeddings("post_url_contents", url_documents, url_ids, metadatas=url_metadatas)

    """
        Generate embeddings for a list of comments and add them to the database.
    """
    def embed_comments(self, comments):
        text_documents = [comment.text for comment in comments]
        text_ids = [str(comment.id) for comment in comments]
        self.create_embeddings("comment_text_contents", text_documents, text_ids)

    """
        Retrieve embeddings from a given collection, with specified filters.
    """
    def get_embeddings(self, collection_name, ids=None, where=None):
        collection = self.get_collection(name=collection_name)
        embeddings = collection.get(ids=ids, where=where, include=["embeddings"])
        return embeddings

    """
        Return embeddings for a user profile of a given username.
    """
    def get_user_profile_embeddings(self, username):
        about = self.get_embeddings("user_abouts", ids=[username])
        text_samples = self.get_embeddings("user_text_samples", where={"username": username})
        beliefs = self.get_embeddings("user_beliefs", where={"username": username})
        interests = self.get_embeddings("user_interests", where={"username": username})

        return {
            "about": about["embeddings"],
            "text_samples": text_samples["embeddings"],
            "beliefs": beliefs["embeddings"],
            "interests": interests["embeddings"]
        }

    """
        Return embeddings for a given post ID.
    """
    def get_post_embeddings(self, post_id):
        title = self.get_embeddings("post_titles", ids=[str(post_id)])
        text_content = self.get_embeddings("post_text_contents", ids=[str(post_id)])
        url_content = self.get_embeddings("post_url_contents", ids=[str(post_id)])

        return {
            "title": title["embeddings"],
            "text_content": text_content["embeddings"],
            "url_content": url_content["embeddings"]
        }

    """
        Return embeddings for a list of comment IDs.
    """
    def get_comment_embeddings(self, comment_id):
        text_content = self.get_embeddings("comment_text_contents", ids=[str(comment_id)])

        return {
            "text_content": text_content["embeddings"]
        }

