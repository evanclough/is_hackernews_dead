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

        self.atts = [
            {"datatype": "user_profile", "name": "about", "list": False},
            {"datatype": "user_profile", "name": "text_samples", "list": True},
            {"datatype": "user_profile", "name": "beliefs", "list": True},
            {"datatype": "user_profile", "name": "interests", "list": True},
            {"datatype": "post", "name": "title", "list": False},
            {"datatype": "post", "name": "text", "list": False},
            {"datatype": "post", "name": "url_content", "list": False},
            {"datatype": "comment", "name": "text", "list": False}
        ]
        self.get_id_att = lambda datatype: "username" if datatype == "user_profile" else "id"

        if create:
            self._create()

    """
        Create collections for each text attribute in the three datatypes
    """
    def _create(self):
        for att in self.atts:
            self.client.create_collection(name=f"{att['datatype']}_{att['name']}", embedding_function=self.embedding_function)
        
    """
        Get a collection of a given attribute for a given datatype.
    """
    def get_collection(self, datatype, att):
        return self.client.get_collection(name=f"{datatype}_{att}", embedding_function=self.embedding_function)

    """
        Create embeddings for a given collection, with given input
        (return if given empty array, for some reason chroma throws an error)
    """
    def create_embeddings(self, datatype, att, documents, ids, metadatas=None, update=False):
        if len(documents) != len(ids):
            raise ChromaError("Error creating embeddings: provided list of documents differs in length from list of ids.")
        if metadatas != None:
            if len(metadatas) != len(ids):
                raise ChromaError("Error creating embeddings: provided list of metadata differs in length from documents and ids.")

        if len(documents) == 0:
            print(f"Attempted to create embeddings of {datatype}_{att} for ids {ids} with empty list of documents. Returning...")
            return

        collection = self.get_collection(datatype, att)

        operation = collection.update if update else collection.add

        operation(documents=documents, ids=ids, metadatas=metadatas)

    """
        Generate embeddings for a given attribute in a given dict list.
    """
    def embed_attribute(self, datatype, att, id_att, is_list_att, dict_list, update=False):
        if is_list_att:
            flattened = functools.reduce(lambda acc, d: [*acc, *[{"doc": list_att_item, "query_att": {"query_att": d[id_att]}, "id": uuid.uuid4()} for list_att_item in d[att] if list_att_item != ""]], dict_list, [])
            documents = [d["doc"] for d in flattened]
            ids = [str(d["id"]) for d in flattened]
            metadatas = [d["query_att"] for d in flattened]
        else:
            dict_list = [d for d in dict_list if d[att] != ""]
            documents = [d[att] for d in dict_list]
            ids = [str(d[id_att]) for d in dict_list]
            metadatas = None
        
        self.create_embeddings(datatype, att, documents, ids, metadatas=metadatas, update=update)
        
    """
        Generate embeddings for a list of dicts representing one of the three datatypes
    """
    def embed_datatype(self, datatype, dict_list):
        datatype_atts = [att for att in self.atts if att["datatype"] == datatype]
        for att in datatype_atts:
            self.embed_attribute(att["datatype"], att["name"], self.get_id_att(datatype), att["list"], dict_list)
    
    """
        Retrieve embeddings from a given collection, with specified filters.
    """
    def get_embeddings_for_attribute(self, datatype, att, ids=None, where=None):
        collection = self.get_collection(datatype, att)
        embeddings = collection.get(ids=ids, where=where, include=["embeddings"])
        return embeddings["embeddings"]

    """
        Retrieve embeddings for one of the three base datatypes, given a list of ids.
    """
    def get_embeddings_for_datatype(self, datatype, id_list):
        datatype_atts = [att for att in self.atts if att["datatype"] == datatype]
        embeddings = []
        for i in id_list:
            id_embeddings = {}
            for att in datatype_atts:
                id_embeddings[att["name"]] = self.get_embeddings_for_attribute(att["datatype"], att["name"], ids=(None if att["list"] else [str(i)]), where=({"query_att": str(i)} if att["list"] else None))
            embeddings.append(id_embeddings)
        return embeddings              

    """
        Remove embeddings for a given collection, with given input.
    """
    def remove_embeddings_for_attribute(self, datatype, att, ids=None, where=None):
        if ids == None and where == None:
            raise ChromaError("Error: attempted to remove embeddings without specified ids or where filter.")

        collection = self.get_collection(datatype, att)
        collection.delete(ids=ids, where=where)

    """
        Remove all embeddings for a specified datatype, with a given id list
    """
    def remove_embeddings_for_datatype(self, datatype, id_list):
        datatype_atts = [att for att in self.atts if att["datatype"] == datatype]
        for att in datatype_atts:
            if att["list"]:
                for i in id_list:
                    self.remove_embeddings_for_attribute(att["datatype"], att["name"], where={"query_att": str(i)})
            else:
                self.remove_embeddings_for_attribute(att["datatype"], att["name"], ids=[str(i) for i in id_list]) 

    """
        Update embeddings for a given attribute in a given dict list.
        If the attribute is a list attribute, since the IDs are random,
        all old ones are just removed and new ones are inserted as new.
    """
    def update_embeddings_for_attribute(self, datatype, att, id_att, is_list_att, dict_list):
        if is_list_att:
            for d in dict_list:
                self.remove_embeddings_for_attribute(datatype, att, where={"query_att": d[id_att]})
            self.embed_attribute(datatype, att, id_att, is_list_att, dict_list)
        else:
            self.embed_attribute(datatype, att, id_att, is_list_att, dict_list, update=True)

    """
        Update embeddings for a given datatype for a given list of dicts.
    """
    def update_embeddings_for_datatype(self, datatype, dict_list, atts=None):
        datatype_atts = [att for att in self.atts if att["datatype"] == datatype and (True if atts == None else (att["name"] in atts))]
        for att in datatype_atts:
            self.update_embeddings_for_attribute(att["datatype"], att["name"], self.get_id_att(datatype), att["list"], dict_list)
    