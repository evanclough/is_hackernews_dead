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
        (return if given empty array, for some reason chroma throws an error)
    """
    def create_embeddings(self, collection_name, documents, ids, metadatas=None):
        if len(documents) != len(ids):
            raise ChromaError("Error creating embeddings: provided list of documents differs in length from list of ids.")
        if metadatas != None:
            if len(metadatas) != len(ids):
                raise ChromaError("Error creating embeddings: provided list of metadata differs in length from documents and ids.")

        if len(documents) == 0:
            return

        collection = self.get_collection(name=collection_name)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    """
        Generate embeddings for a list of user profile dictionaries.
    """
    def embed_user_profiles(self, user_dict_list):

        filtered_for_about = [user_dict for user_dict in user_dict_list if user_dict["about"] != ""]
        about_documents = [user_dict["about"] for user_dict in filtered_for_about]
        about_ids = [user_dict["username"] for user_dict in filtered_for_about]
        self.create_embeddings("user_abouts", about_documents, about_ids)

        list_cols = ["text_samples", "beliefs", "interests"]
        for list_col in list_cols:
            filtered = [user_dict for user_dict in user_dict_list if len(user_dict[list_col]) > 0]
            flattened_text_samples = functools.reduce(lambda acc, t: [*acc, *[{"text": te, "username": t["username"], "id": uuid.uuid4()}for te in t[list_col]]], filtered, [])
            documents = [t["text"] for t in flattened_text_samples]
            ids = [str(uuid.uuid4()) for t in flattened_text_samples]
            metadatas = [{"username": t["username"]} for t in flattened_text_samples]
            self.create_embeddings(f"user_{list_col}", documents, ids, metadatas=metadatas)

    """
        Generate embeddings for a list of post dicts and add them to the database.
    """
    def embed_posts(self, post_dict_list):
        title_documents = [post["title"] for post in post_dict_list]
        title_ids = [str(post["id"]) for post in post_dict_list]
        self.create_embeddings("post_titles", title_documents, title_ids)

        filtered_for_text = [post for post in post_dict_list if post["text"] != ""]
        text_documents = [post["text"] for post in filtered_for_text]
        text_ids = [str(post["id"]) for post in filtered_for_text]
        self.create_embeddings("post_text_contents", text_documents, text_ids)

        filtered_for_url = [post for post in post_dict_list if post["url_content"] != ""]
        url_documents = [post["url_content"] for post in filtered_for_url]
        url_ids = [str(post["id"]) for post in filtered_for_url]
        url_metadatas = [{"url": post["url"]} for post in filtered_for_url]
        self.create_embeddings("post_url_contents", url_documents, url_ids, metadatas=url_metadatas)

    """
        Generate embeddings for a list of comment dicts and add them to the database.
    """
    def embed_comments(self, comment_dict_list):
        text_documents = [comment["text"] for comment in comment_dict_list]
        text_ids = [str(comment["id"]) for comment in comment_dict_list]
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

    """
        Remove embeddings for a given collection, with given input.
    """
    def remove_embeddings(self, collection_name, ids=None, where=None):
        if ids == None and where == None:
            raise ChromaError("Error: attempted to remove embeddings without specified ids or where filter.")
        collection = self.get_collection(collection_name)
        collection.delete(ids=ids, where=where)

    """
        Remove embeddings for a list of given usernames.
    """
    def remove_user_profile_embeddings(self, usernames):
        self.remove_embeddings("user_abouts", ids=usernames)
        for username in usernames:
            self.remove_embeddings("user_text_samples", where={"username": username})
            self.remove_embeddings("user_beliefs", where={"username": username})
            self.remove_embeddings("user_interests", where={"username": username})


    """
        Remove embeddings for a list of post ids.
    """
    def remove_post_embeddings(self, post_ids):
        str_ids = [str(post_id) for post_id in post_ids]
        self.remove_embeddings("post_titles", ids=str_ids)
        self.remove_embeddings("post_text_contents", ids=str_ids)
        self.remove_embeddings("post_url_contents", ids=str_ids)

    """
        Remove embeddings for a list of comment ids.
    """
    def remove_comment_embeddings(self, comment_ids):
        str_ids = [str(comment_id) for comment_id in comment_ids]
        self.remove_embeddings("comment_text_contents", ids=str_ids)
