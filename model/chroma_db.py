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

class EmbeddingsNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)

class GenerateNullEmbeddingsError(Exception):
    def __init__(self, message):
        super().__init__(message)


"""
    A class used to create the object with which the dataset
    will interact with Chroma

    (wanted to do this the same way i did sqlite with connection only being open when necessary,
    but looks like chroma doesnt have functionality for that. oh well.)
"""
class ChromaDB:
    def __init__(self, path, forum, embedding_model):
        self.path = path

        self.embedding_model = embedding_model

        self.client = chromadb.PersistentClient(path=self.path)

        self.check_update_collections(forum)

    def check_update_collections(self, forum):
        collection_names = self.client.list_collections()

        for entity_model in forum.get_entity_models():
            for att in entity_model.all_embedded_atts():
                collection_name = f"{entity_model.table_name}_{att.name}"
                if not (att_collection_name in collection_names):
                    self.client.create_collection(name=att_collection_name,
                        embedding_function=self.embedding_model.get_chroma_embedding_function())
    
    """
        Get a collection of a given attribute for a given entity.
    """
    def get_collection(self, table_name, att_name):
        return self.client.get_collection(name=f"{table_name}_{att_name}", embedding_function=self.embedding_model.get_chroma_embedding_function())


    """
        Generate embeddings for a given attribute of a given entity type,
        given an id list and a value list
    """
    def generate(self, att_model, id_list, value_list, update=False):
        documents = [val for val in value_list]
        ids = [str(id_val) for id_val in id_list]

        if len(documents) != len(ids):
            raise ChromaError("Error creating embeddings: provided list of documents differs in length from list of ids.")
        if len(documents) == 0:
            raise GenerateNullEmbeddingsError(f"Attempted to create embeddings for {att_model.name} for ids {ids} with empty list of documents.")
        for doc in documents:
            if doc == None:
                raise GenerateNullEmbeddingsError(f"Error: attempted to generate embeddings for unfilled attribute for {att_model.name} for ids {ids}.")

        documents = [("EMPTY" if doc == "" else doc) for doc in documents]

        for i in range(len(documents)):
            if self.embedding_model.tokenize(documents[i]) > self.embedding_model.max_tokens:
                raise ChromaError(f"Error: attempted to generate embeddings for document with id {metadatas[i]['id_val'] if att_model['is_list'] else ids[i]}")

        collection = self.get_collection(att_model.table_name, att_model.name)

        operation = collection.update if update else collection.add

        operation(documents=documents, ids=ids)

    """
        Retrieve embeddings for a given id list
    """
    def retrieve(self, att_model, id_val):

        collection = self.get_collection(att_model.table_name, att_model.name)

        ids = [str(id_val)]

        result = collection.get(ids=ids, include=["documents", "embeddings"])

        values = ["" if doc == "EMPTY" else doc for doc in result['documents']]

        if len(result['embeddings']) == 0:
            raise EmbeddingsNotFoundError(f"Error: embeddings for attribute {att_model.name} of {att_model.table_name} with id {id_val} not found.")

        return {'embeddings': result['embeddings'][0], 'value': values[0]}


    def delete(self, att_model, id_list):
        collection = self.get_collection(att_model.table_name, att_model.name)
        collection.delete(ids=[str(id_val) for id_val in id_list])

    def update(self, att_model, id_list, value_list):
        self.generate(att_model, id_list, value_list, update=True)
