"""
    A file to hold the dataset class to be used in training and running the model.
"""

import datetime
import json
import functools

import utils
import sqlite_db
import chroma_db
import user_pool
import submission_forest
import HN_entities
import llms
import embeddings

"""
    An exception class for general dataset errors.
"""
class DatasetError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Dataset:
    def __init__(self, name, entity_classes, data_source_file_names=None, llm_config=None, embedding_config=None, verbose=False):

        self.name = name
        self.entity_classes = entity_classes
        self.verbose = verbose
        
        self.dataset_path = utils.get_dataset_path(self.name)

        if not utils.check_directory_exists(self.dataset_path):
            utils.create_directory(self.dataset_path)

        if data_source_file_names == None:
            self.data_source_file_names = utils.read_json(utils.fetch_env_var("DEFAULT_DATA_SOURCE_FILE_NAMES"))
        else:
            self.data_source_file_names = data_source_file_names

        self.user_pool_path = self.get_data_source_path(self.data_source_file_names["user_pool_path"])
        self.sf_path = self.get_data_source_path(self.data_source_file_names["sf_path"])
        self.entity_models_path = self.get_data_source_path(self.data_source_file_names["entity_models_path"])
        self.sqlite_path = self.get_data_source_path(self.data_source_file_names["sqlite_path"])
        self.chroma_path = self.get_data_source_path(self.data_source_file_names["chroma_path"])

        if utils.check_file_exists(self.entity_models_path):
            self.entity_models = utils.read_json(self.entity_models_path)
        else:
            self.entity_models = utils.read_json(utils.fetch_env_var("DEFAULT_ENTITY_MODELS"))

        self.sqlite = sqlite_db.SqliteDB(self.sqlite_path, self.entity_models)

        if embedding_config == None:
            self.embedding_config = utils.read_json(utils.fetch_env_var("DEFAULT_EMBEDDING_CONFIG"))
        else:
            self.embedding_config = embedding_config

        self.embedding_model = embeddings.get_embedding_model(self.embedding_config)

        self.chroma = chroma_db.ChromaDB(self.chroma_path, self.entity_models, self.embedding_model)

        if llm_config == None:
            self.llm_config = utils.read_json(utils.fetch_env_var("DEFAULT_LLM_CONFIG"))
        else:
            self.llm_config = llm_config

        self.llm = llms.get_llm(self.llm_config)

        has_sf = utils.check_file_exists(self.sf_path)
        if has_sf:
            self.sf = submission_forest.SubmissionForest(self.name, utils.read_json(self.sf_path), self.entity_factory, self.sqlite, self.chroma, verbose=self.verbose)
        else:
            self.sf = submission_forest.SubmissionForest(self.name, [], self.entity_factory, self.sqlite, self.chroma, verbose=self.verbose)
            self.write_current_sf()

        has_user_pool = utils.check_file_exists(self.user_pool_path)
        if has_user_pool:
            self.user_pool = user_pool.UserPool(self.name, utils.read_json(self.user_pool_path), self.entity_factory, self.sqlite, self.chroma, verbose=self.verbose)
        else:
            self.user_pool = user_pool.UserPool(self.name, [], self.entity_factory, self.sqlite, self.chroma, verbose=self.verbose)
            self.write_current_user_pool()

    
    def entity_factory(self, entity_type, id_val, loader):
        return self.entity_classes[entity_type](self.entity_models[entity_type], id_val, loader, self.sqlite, self.chroma, verbose=self.verbose)


    def get_data_source_path(self, filename):
        return self.dataset_path + "/" + filename

    def _print(self, s):
        if self.verbose:
            print(s)

    def set_verbose(self, verbose):
        self.verbose = verbose
    
    def __str__(self):
        return f"Dataset {self.name}"

    def get_name(self):
        return self.name

    def get_initial_time(self):
        return self.initial_time
    
    def get_current_time(self):
        return self.current_time

    """
        Write the current user pool to a JSON.
    """
    def write_current_user_pool(self):
        current_uids = self.user_pool.get_uids()
        utils.write_json(current_uids, self.user_pool_path)

    """
        Write the current potential response forest to a JSON.
    """
    def write_current_sf(self):
        current_sf = self.sf.convert_to_st_dict_list()
        utils.write_json(current_sf, self.sf_path)

    """
        Advance the current time by a given amount.
    """
    def advance_current_time(self, amount):
        self.current_time += amount

    """
        Initialize the dataset for a run.
    """
    def initialize_for_run(self, initial_time=None):
        self._print(f"Initializing dataset {self.name} for run...")

        self._print("Cleaning user pool...")
        self.user_pool.clean(sqlite_db=self.sqlite_db, chroma_db=self.chroma_db, check_base_atts=True, check_derived_atts=True, check_embeddings=True)

        self._print("Cleaning submission response forest...")
        self.sf.clean(sqlite_db=self.sqlite_db, chroma_db=self.chroma_db, check_base_atts=True, check_derived_atts=True, check_embeddings=True)

        if initial_time == None:
            self._print("Finding initial time...")
            root_times = self.sf.get_root_times(self.sqlite_db)
            try:
                latest_time = max(root_post_times)
            except ValueError as e:
                print("Error finding latest time among current roots, they are likely empty.")
                print("This dataset is not ready for a run. Returning...")
                return
            self.initial_time = latest_time + 1
        else:
            self.initial_time = initial_time

        self.current_time = self.initial_time

        self._print(f"Initial time: {datetime.datetime.fromtimestamp(self.initial_time)}")

        self._print(f"Successfully initialized dataset {self} for run.")


    """
        Get a cost estimate for creating embeddings for a list of dicts.
    """
    def embedding_cost_estimate():
        return
