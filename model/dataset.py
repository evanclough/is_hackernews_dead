"""
    A file to hold the dataset class to be used in training and running the model.
"""

import datetime
import json
import functools

from openai import OpenAI

import utils
import sqlite_db
import chroma_db
import user_pool
import submission_forest
import HN_entities

"""
    An exception class for general dataset errors.
"""
class DatasetError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Dataset:
    def __init__(self, name, entity_classes, data_source_file_names=None, embedding_config=None, verbose=False):

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

        self.chroma = chroma_db.ChromaDB(self.chroma_path, self.entity_models, self.embedding_config)

        has_sf = utils.check_file_exists(self.sf_path)
        if has_sf:
            self.sf = submission_forest.SubmissionForest(self.name, utils.read_json(self.sf_path), self.entity_factory, self.sqlite, self.chroma, verbose=self.verbose)
        else:
            self.sf = submission_forest.SubmissionForest(self.name, [], self.entity_factory, verbose=self.verbose)
            self.write_current_sf()

        has_user_pool = utils.check_file_exists(self.user_pool_path)
        if has_user_pool:
            self.user_pool = user_pool.UserPool(self.name, utils.read_json(self.user_pool_path), self.entity_factory, self.sqlite, self.chroma, verbose=self.verbose)
        else:
            self.user_pool = user_pool.UserPool(self.name, [], self.entity_factory, verbose=self.verbose)
            self.write_current_user_pool()


    def embed(self, user_pool, user_check={}, submission_derived_sources={}, submission_checklist={}):
        self._print(f"Generating and storing embeddings for dataset {self}...")

        self._print(f"Generating and storing embeddings for user pool...")

        up_base_loader = entities.BaseLoader(source=entities.BaseSources.SQLITE)
        up_derived_loader = entities.DerivedLoader(kwarg_dict=up_kwarg_dict)
        up_loader = entities.EntityLoader(base=up_base_loader, derived=up_derived_loader)

        self.user_pool.clean(load=up_loader, checklist=user_checklist)

        user_objects = self.user_pool.fetch_all_user_objects(load=user_load_dict)

        for user in user_objects:
            user.generate_embeddings(self.chroma)

        self._print(f"Successfully generated and stored embeddings for user pool.")

        self._print(f"Generating and storing embeddings for submission forest...")

        submission_load_dict = {
            'base': {'sqlite': self.sqlite}, 
            'derived': {'sqlite': self.sqlite, 'other': submission_derived_sources}
        }

        self.sf.clean(load=submission_load_dict, checklist=submission_checklist)

        self.sf.dfs_roots(lambda s: s['sub_obj'].generate_embeddings(self.chroma), load=submission_load_dict)

        self._print(f"Successfully generated and stored embeddings for submission forest.")
    
    def entity_factory(self, entity_type, id_val, loader):
        return self.entity_classes[entity_type](self.entity_models[entity_type], id_val, self.fill_loader(loader), verbose=self.verbose)

    def fill_loader(self, loader):
        loader.sqlite = self.sqlite
        if loader.needs_sqlite:
            loader.sqlite = self.sqlite
        if loader.needs_chroma:
            loader.chroma = self.chroma

        return loader


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
        Add a set of users to the dataset, given a list of attribute dicts.
    """
    def add_users(self, user_dict_list, check_submission_history=False):
        try:
            uid_list = [user_dict["username"] for user_dict in user_dict_list]

            self._print("Adding users")
            for uid in uid_list:
                self._print(uid)
            self._print("to the dataset...")

            self.user_pool.add_uids(uid_list)

            self._print("Putting into sqlite...")
            self.sqlite_db.insert_entity("users", user_dict_list) 

            if self.has_chroma:
                self._print("Generating embeddings...")
                self.chroma_db.embed_entity("users", user_dict_list)

            self.write_current_user_pool()

            self._print("Successfully added users")
            for uid in uid_list:
                self._print(uid)
            self._print("to the dataset.")

            return True
        except Exception as e:
            print(f"Error adding users to {self}:")
            utils.print_error(e)
            return False

    """
        Remove a list of users from the dataset, given their uids.
    """
    def remove_users(self, uid_list, remove_posts=False, remove_comments=False):
        try:

            self._print("Removing users:")
            for uid in uid_list:
                self._print(uid)
            if remove_posts:
                self._print("and all of their posts")
            if remove_comments:
                self._print("and all of their comments")
            self._print("from the dataset...")

            user_profiles = self.user_pool.fetch_some_users(uid_list, self.sqlite_db)

            if remove_posts:
                for user_profile in user_profiles:
                    post_ids = user_profile.get_att("post_ids")
                    self.remove_root_posts(post_ids)
            if remove_comments:
                for user_profile in user_profiles:
                    comment_ids = user_profile.get_att("comment_ids")
                    self.remove_comments(comment_ids)

            self._print("Removing from sqlite...")
            self.sqlite_db.delete_entities_by_identifier_list("users", uid_list)

            if self.has_chroma:
                self._print("Removing embeddings...")
                self.chroma_db.remove_embeddings_for_datatype("user_profile", uid_list)

            self.user_pool.remove_uids(uid_list)

            self.write_current_user_pool()

            self._print("Successfully removed users:")
            for uid in uid_list:
                self._print(uid)
            if remove_posts:
                self._print("and all of their posts")
            if remove_comments:
                self._print("and all of their comments")
            self._print("from the dataset.")

            return True
        except Exception as e:
            print("Error removing users from the dataset:")
            utils.print_error(e)
            return False

    """
        Add a set of new root posts to the dataset, given a list of attribute dicts
    """
    def add_root_posts(self, post_dict_list, update_author_profile=False):
        try:
            self._print("Adding root posts:")
            for post_dict in post_dict_list:
                self._print(post_dict["id"])
            self._print("to the dataset...")

            self.prf.add_roots([post_dict["id"] for post_dict in post_dict_list])

            self._print("Putting into sqlite...")
            self.sqlite_db.insert_entity("roots", post_dict_list)
            
            if update_author_profile:
                self._print("Updating authors post histories in sqlite...")

                author_post_map = {}
                for post_dict in post_dict_list:
                    author_uid = post_dict["by"]
                    post_id = post_dict["id"]
                    if author_uid in author_post_map:
                        author_post_map[author_uid].append(post_id)
                    else:
                        author_post_map[author_uid] = [post_id]

                for uid, user_new_post_ids in author_post_map.items():
                    user_profile = entities.User(uid, sqlite_db=self.sqlite_db)
                    updated_post_ids = [*user_profile.get_att("post_ids"), *user_new_post_ids]
                    update_dict = {"post_ids": json.dumps(updated_post_ids)}
                    self.sqlite_db.update_entities_by_identifier_list("users", [uid], update_dict)

            if self.has_chroma:
                self._print("Generating embeddings...")
                self.chroma_db.embed_entity("roots", post_dict_list)

            self.write_current_sf()

            self._print("Successfully added root posts")
            for post_dict in post_dict_list:
                self._print(post_dict["id"])
            self._print("to the dataset.")

            return True
        except Exception as e:
            print("Error adding roots to {self}")
            utils.print_error(e)
            return False

    """
        Remove a list of root posts from the dataset, given their ids.
    """
    def remove_root_posts(self, post_ids, update_author_profile=False):
        try:

            self._print("Removing root posts:")
            for post_id in post_ids:
                self._print(post_id)
            self._print("from the dataset...")

            all_kid_ids = []
            for post_id in post_ids:
                post = self.prf.get_item(post_id)
                kids = post.get_kids()
                kid_ids = [kid.get_id() for kid in kids]
                all_kid_ids = [*all_kid_ids, *kid_ids]
            self.remove_comments(all_kid_ids, update_author_profile=update_author_profile)
            
            if update_author_profile:
                self._print("Updating authors post histories in sqlite...")

                author_post_map = {}
                for post_id in post_ids:
                    post = self.prf.get_item(post_id)
                    post_contents = post.fetch_contents(sqlite_db=self.sqlite_db)
                    author_uid = post_contents.get_att("by")
                    if author_uid in author_post_map:
                        author_post_map[author_uid].append(post_id)
                    else:
                        author_post_map[author_uid] = [post_id]

                for uid, user_post_ids_to_remove in author_post_map.items():
                    user_profile = entities.User(uid, sqlite_db=self.sqlite_db)
                    updated_post_ids = [pid for pid in user_profile.get_att("post_ids") if not (pid in user_post_ids_to_remove)]
                    update_dict = {"post_ids": json.dumps(updated_post_ids)}
                    self.sqlite_db.update_entities_by_identifier_list("users", [uid], update_dict)

            self._print("Removing from sqlite...")
            self.sqlite_db.delete_entities_by_identifier_list("roots", post_ids)

            if self.has_chroma:
                self._print("Removing embeddings...")
                self.chroma_db.remove_embeddings_for_datatype("post", post_ids)

            self.prf.remove_roots(post_ids)

            self.write_current_sf()

            self._print("Successfully removed root posts with ids:")
            for post_id in post_ids:
                self._print(post_id)
            self._print("from the dataset.")

            return True
        except Exception as e:
            print("Error removing root posts from the dataset:")
            utils.print_error(e)
            return False

    """
        Add a list of leaf comments to the dataset, 
        given a list of dicts including their attributes.
    """
    def add_leaf_comments(self, leaf_dict_list, update_author_profile=False):
        try:
            self._print("Adding leaf comments:")
            for leaf_dict in leaf_dict_list:
                self._print(leaf_dict["id"])
            self._print("to the dataset...")

            for leaf_dict in leaf_dict_list:
                parent_id = leaf_dict["parent"]
                parent = self.prf.get_item(parent_id)
                parent.add_kid(leaf_dict["id"])

            self._print("Putting into sqlite...")
            self.sqlite_db.insert_entity("comments", leaf_dict_list)

            if update_author_profile:
                self._print("Updating authors comment histories in sqlite...")

                author_comment_map = {}
                for leaf_dict in leaf_dict_list:
                    author_uid = leaf_dict["by"]
                    leaf_id = leaf_dict["id"]
                    if author_uid in author_comment_map:
                        author_comment_map[author_uid].append(leaf_id)
                    else:
                        author_comment_map[author_uid] = [leaf_id]

                for uid, user_new_comment_ids in author_comment_map.items():
                    user_profile = entities.User(uid, sqlite_db=self.sqlite_db)
                    updated_comment_ids = [*user_profile.get_att("comment_ids"), *user_new_comment_ids]
                    update_dict = {"comment_ids": json.dumps(updated_comment_ids)}
                    self.sqlite_db.update_entities_by_identifier_list("users", [uid], update_dict)

            if self.has_chroma:
                self._print("Generating embeddings...")
                self.chroma_db.embed_entity("branches", leaf_dict_list)

            self.write_current_sf()

            self._print("Succesfully added leaf comments")
            for leaf_dict in leaf_dict_list:
                self._print(leaf_dict["id"])
            self._print("to the dataset.")

            return True
        except Exception as e:
            print("Error adding comments to dataset:")
            utils.print_error(e)
            return False

    """
        Remove a list of comments from the dataset, and all of their descendants, given a list of ids.
        (passing in non-existing comment ids is chill here)
    """
    def remove_comments(self, comment_ids, update_author_profile=False):
        try:
            self._print("Removing comments:")
            for comment_id in comment_ids:
                self._print(comment_id)
            self._print("and all of their descendants from the dataset...")

            all_comments_to_remove = []

            for comment_id in comment_ids:
                try:
                    comment = self.prf.get_item(comment_id)
                except potential_responses.PotentialResponseForestError as e:
                    self._print(f"Attempted to remove comment with id {comment_id} which does not exist in potential response forest. Skipping...")
                    continue
                comment_and_descendants = [dec for dec in comment.get_flattened_descendants()]
                all_comments_to_remove = [*all_comments_to_remove, *comment_and_descendants]
            
            self._print("Full list of comments to be removed, including descendants:")
            for comment in all_comments_to_remove:
                self._print(comment.get_id())

            all_comment_ids_to_remove = [comment.get_id() for comment in all_comments_to_remove]
            unique_comment_ids_to_remove = list(set(all_comment_ids_to_remove))

            if update_author_profile:
                self._print("Updating author comment histories in sqlite...")

                comment_contents = [comment.fetch_contents(sqlite_db=self.sqlite_db) for comment in all_comments_to_remove]

                author_comment_map = {}

                for comment in comment_contents:
                    author_uid = comment.get_att("by")
                    if author_uid in author_comment_map:
                        author_comment_map[author_uid].append(comment.get_att("id"))
                    else:
                        author_comment_map[author_uid] = [comment.get_att("id")]
                
                for uid, user_comment_ids_to_remove in author_comment_map.items():
                    unique_comment_ids = list(set(user_comment_ids_to_remove))
                    user_profile = entities.User(uid, sqlite_db=self.sqlite_db)
                    updated_comment_ids = [cid for cid in user_profile.get_att("comment_ids") if not (cid in unique_comment_ids)]
                    update_dict = {"comment_ids": json.dumps(updated_comment_ids)}
                    self.sqlite_db.update_entities_by_identifier_list("users", [uid], update_dict)

            self._print("Removing from sqlite...")
            self.sqlite_db.delete_entities_by_identifier_list("comments", unique_comment_ids_to_remove)

            if self.has_chroma:
                self._print("Removing embeddings...")
                self.chroma_db.remove_embeddings_for_datatype("comment", unique_comment_ids_to_remove)

            self.prf.remove_items(comment_ids)

            self.write_current_sf()

            self._print("Successfully removed comments with ids:")
            for comment_id in comment_ids:
                self._print(comment_id)
            self._print("and all of their descendants from the dataset.")

            return True
        except Exception as e:
            print("Error removing leaf comments from the dataset:")
            utils.print_error(e)
            return False

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
