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
    def __init__(self, path, entity_models, embedding_model):
        self.path = path

        self.embedding_model = embedding_model

        self.client = chromadb.PersistentClient(path=self.path)

        self.check_update_collections(entity_models)

    def check_update_collections(self, entity_models):
        collection_names = self.client.list_collections()
        for entity_model in entity_models.values():
            for att_model_list in entity_model['attributes'].values():
                for att_model in att_model_list:
                    if att_model['embed']:
                        att_collection_name = f"{entity_model['table_name']}_{att_model['name']}"
                        if not (att_collection_name in collection_names):
                            self.client.create_collection(name=att_collection_name,
                                embedding_function=self.embedding_model.get_chroma_embedding_function())
    
    """
        Get a collection of a given attribute for a given entity.
    """
    def get_collection(self, entity_model, att):
        return self.client.get_collection(name=f"{entity_model['table_name']}_{att}", embedding_function=self.embedding_model.get_chroma_embedding_function())


    """
        Generate embeddings for a given attribute of a given entity type,
        given an id list and a value list
    """
    def generate(self, entity_model, att_model, id_list, value_list, update=False):

        
        if att_model['is_list']:
            list_val_dicts = utils.flatten_array([[
                {
                    "doc": val,
                    "metadata": {"id_val": id_val},
                    "id": str(uuid.uuid4())
                } for vals in list_val] for id_val, list_val in list(zip(id_list, value_list))])
            documents = [d["doc"] for d in list_val_dicts]
            ids = [d["id"] for d in list_val_dicts]
            metadatas = [d["metadata"] for d in list_val_dicts]
        else:
            documents = [val for val in value_list]
            ids = [str(id_val) for id_val in id_list]
            metadatas = None

        if len(documents) != len(ids):
            raise ChromaError("Error creating embeddings: provided list of documents differs in length from list of ids.")
        if metadatas != None:
            if len(metadatas) != len(ids):
                raise ChromaError("Error creating embeddings: provided list of metadata differs in length from documents and ids.")
        if len(documents) == 0:
            raise GenerateNullEmbeddingsError(f"Attempted to create embeddings for {att_model['name']} for ids {ids} with empty list of documents.")
        for doc in documents:
            if doc == None:
                raise GenerateNullEmbeddingsError(f"Error: attempted to generate embeddings for unfilled attribute for {att_model['name']} for ids {ids}.")

        documents = [("EMPTY" if doc == "" else doc) for doc in documents]

        for i in range(len(documents)):
            if self.embedding_model.tokenize(documents[i]) > self.embedding_model.max_tokens:
                raise ChromaError(f"Error: attempted to generate embeddings for document with id {metadatas[i]['id_val'] if att_model['is_list'] else ids[i]}")

        collection = self.get_collection(entity_model, att_model['name'])

        operation = collection.update if update else collection.add

        operation(documents=documents, ids=ids, metadatas=metadatas)

    """
        Retrieve embeddings for a given id list
    """
    def retrieve(self, entity_model, att_model, id_val):

        collection = self.get_collection(entity_model, att_model['name'])

        ids = None if att_model['is_list'] else [str(id_val)]
        where = {"id_val": str(id_val)} if att_model['is_list'] else None

        result = collection.get(ids=ids, where=where, include=["documents", "embeddings"])

        values = ["" if doc == "EMPTY" else doc for doc in result['documents']]

        if len(result['embeddings']) == 0:
            raise EmbeddingsNotFoundError(f"Error: embeddings for attribute {att_model['name']} of {entity_model['table_name']} with id {id_val} not found.")
        
        if att_model["is_list"]:
            return [{'embeddings': result['embeddings'][i], 'value': values[i]} for i in range(len(result['embeddings']))]
        else:
            return {'embeddings': result['embeddings'][0], 'value': values[0]}


    def delete(self, entity_model, att_model, id_list):
        collection = self.get_collection(entity_model, att_model['name'])

        if att_model['is_list']:
            for id_val in id_list:
                collection.delete(ids=None, where={"id_att": str(id_val)})
        else:
            collection.delete(ids=[str(id_val) for id_val in id_list])

    def update(self, entity_model, att_model, id_list, value_list):
        if att_model['is_list']:
            self.delete(entity_model, att_model, id_list)
        
        self.generate(entity_model, att_model, id_list, value_list, update=True)
