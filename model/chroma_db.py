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
    def __init__(self, path, entities, embedding_config, create=False):
        self.path = path
        self.entities = entities

        self._truncate = embedding_config["truncate"]
        self._truncate_increment = embedding_config["truncate_increment"]
        self._embedding_model = embedding_config["model"]
        self._embedding_model_max_tokens = embedding_config["max_tokens"]

        self.embedding_function = utils.get_chroma_embedding_function(self._embedding_model)
        self.tokenizer = utils.get_embedding_tokenizer(self._embedding_model)
        self.client = chromadb.PersistentClient(path=self.path)


        if create:
            self._create()

    """
        Get all attributes for a given entity type which are embedded and stored in chroma
    """
    def get_atts(self, entity_type):
        return [att['name'] for att in (self.entities[entity_type]['attributes'].values()) if att['embed']]

    """
        Create collections for each designated attribute for each entity
    """
    def _create(self):
        for entity_type, entity_dict in self.entities.items():
            for att in self.get_atts(entity_type):
                self.client.create_collection(name=f"{entity_dict['table_name']}_{att['name']}", embedding_function=self.embedding_function)
        

    """
        Get a collection of a given attribute for a given entity.
    """
    def get_collection(self, entity_type, att):
        return self.client.get_collection(name=f"{self.entities[entity_type]['table_name']}_{att}", embedding_function=self.embedding_function)

    """
        Create embeddings for a given collection, with given input
        (return if given empty array, for some reason chroma throws an error)
    """
    def create_embeddings(self, entity_type, att, documents, ids, metadatas=None, update=False):
        if len(documents) != len(ids):
            raise ChromaError("Error creating embeddings: provided list of documents differs in length from list of ids.")
        if metadatas != None:
            if len(metadatas) != len(ids):
                raise ChromaError("Error creating embeddings: provided list of metadata differs in length from documents and ids.")

        if len(documents) == 0:
            print(f"Attempted to create embeddings of {entity_type}_{att} for ids {ids} with empty list of documents. Returning...")
            return

        for i in range(len(documents)):
            if self.tokenizer(documents[i]) > self._embedding_model_max_tokens:
                if self._truncate:
                    print(f"Document {entity_type}_{att} with id {ids[i]} exceeds the token maximum for the given embedding model. Truncating until it does...")
                    while self.tokenizer(documents[i]) > self._embedding_model_max_tokens:
                        documents[i] = documents[i][:-self._truncate_increment]
                else:
                    raise ChromaError(f"Document with id {ids[i]} exceeds the token maximum for the given embedding model.")

        collection = self.get_collection(entity_type, att)

        operation = collection.update if update else collection.add

        operation(documents=documents, ids=ids, metadatas=metadatas)

    """
        Generate embeddings for a given attribute in a given dict list representing items of that entity type.
    """
    def embed_attribute(self, entity_type, att_dict, dict_list, update=False):
        if att_dict['is_list']:
            dicts_with_att = [[
                {
                    "doc": list_item,
                    "metadata": {"id_val": d[self.entities[entity_type]['id_att']]},
                    "id": uuid.uuid4()
                } for list_item in d[att_dict['name']] if list_item != ""] for d in dict_list]
            flattened_dicts_with_att = utils.flatten_array(list_att_dicts)
            documents = [d["doc"] for d in flattened_dicts_with_att]
            ids = [str(d["id"]) for d in flattened_dicts_with_att]
            metadatas = [d["metadata"] for d in flattened_dicts_with_att]
        else:
            dicts_with_att = [d for d in dict_list if d[att['name']] != ""]
            documents = [d[att['name']] for d in dicts_with_att]
            ids = [str(d[self.entities[entity_type['id_att']]]) for d in dicts_with_att]
            metadatas = None
        
        self.create_embeddings(entity_type, att['name'], documents, ids, metadatas=metadatas, update=update)
        
    """
        Generate and store embeddings for a list of dicts representing items of a given entity
    """
    def create_embeddings(self, entity_type, dict_list):
        atts_to_embed = self.get_atts(entity_type)
        for att in atts_to_embed:
            self.embed_attribute(entity_type, att, dict_list)

    def store_embeddings_for_id_list(self, entity_type, att_dict, id_list, att_val_list):
        if att_dict['is_list']:
            dicts_with_att = [[
                {
                    "doc": val,
                    "metadata": {"id_val": id_val},
                    "id": str(uuid.uuid4())
                } for vals in vals if val != ""] for id_val, vals in list(zip(id_list, att_val_list))]
            flattened_dicts_with_att = utils.flatten_array(list_att_dicts)
            documents = [d["doc"] for d in flattened_dicts_with_att]
            ids = [d["id"] for d in flattened_dicts_with_att]
            metadatas = [d["metadata"] for d in flattened_dicts_with_att]
        else:
            dicts_with_att = [d for d in dict_list if d[att['name']] != ""]
            documents = [d[att['name']] for d in dicts_with_att]
            ids = [str(d[self.entities[entity_type['id_att']]]) for d in dicts_with_att]
            metadatas = None
        
        self.create_embeddings(entity_type, att['name'], documents, ids, metadatas=metadatas)

    """
        Get embeddings for a given id list
    """
    def get_embeddings_by_id_list(self, entity_type, att_dict, id_list):
        collection = self.get_collection(entity_type, att_dict['name'])

        ids = None if att['is_list'] else [str(id_val) for id_val in id_list]
        where = {"id_val": str(id_val)} if att['is_list'] else None

        embeddings = collection.get(ids=ids, where=where, include=["embeddings"])

        return embeddings["embeddings"]

    """
        Retrieve embeddings from a given collection, with specified filters.
    """
    def get_embeddings_for_attribute(self, entity_type, att, ids=None, where=None):
        collection = self.get_collection(entity_type, att)
        embeddings = collection.get(ids=ids, where=where, include=["embeddings"])
        return embeddings["embeddings"]

    """
        Retrieve embeddings for given a list of ids representing items of a given entity.
    """
    def get_embeddings(self, entity_type, id_list):
        embedded_atts = self.get_atts(entity_type)
        embeddings = []
        for id_val in id_list:
            embeddings_dicts = {}
            for att in embedded_atts:
                ids = None if att['is_list'] else [str(id_val)]
                where = {"id_val": str(id_val)} if att['is_list'] else None
                embeddings_dicts[att["name"]] = self.get_embeddings_for_attribute(entity_type, att["name"], ids=ids, where=where)
            embeddings.append(embeddings_dicts)
        return embeddings              

    """
        Remove embeddings for a given collection, with given input.
    """
    def remove_embeddings_for_attribute(self, entity_type, att, ids=None, where=None):
        if ids == None and where == None:
            raise ChromaError("Error: attempted to remove embeddings without specified ids or where filter.")

        collection = self.get_collection(entity_type, att)
        collection.delete(ids=ids, where=where)

    """
        Remove all embeddings for a specified entity, with a given id list
    """
    def remove_embeddings(self, entity_type, id_list):
        embedded_atts = self.get_atts(entity_type)
        for att in embedded_atts:
            if att['is_list']:
                for id_val in id_list:
                    self.remove_embeddings_for_attribute(entity_type, att["name"], where={"id_att": str(id_val)})
            else:
                self.remove_embeddings_for_attribute(entity_type, att["name"], ids=[str(id_val) for id_val in id_list]) 

    """
        Update embeddings for a given attribute in a given dict list.
        If the attribute is a list attribute, since the IDs are random,
        all old ones are just removed and new ones are inserted as new.
    """
    def update_embeddings_for_attribute(self, entity_type, att_dict, dict_list):
        if att_dict['is_list']:
            for d in dict_list:
                self.remove_embeddings_for_attribute(entity, att, where={"id_val": d[self.entities[entity_type]['id_att']]})
            self.embed_attribute(entity_type, att_dict, dict_list)
        else:
            self.embed_attribute(entity_type, att_dict, dict_list, update=True)

    """
        Update embeddings for a given entity for a given list of dicts.
        If a list of attributes to include in the update is provided, only they will be updated,
        otherwise, all will.
    """
    def update_embeddings(self, entity_type, dict_list, included_atts=None):
        embedded_atts = self.get_atts(entity_type)

        atts_to_update = [att for att in embedded_atts if (True if included_atts == None else (att["name"] in included_atts))]

        for att_dict in atts_to_update:
            self.update_embeddings_for_attribute(entity_type, att_dict, dict_list)
    