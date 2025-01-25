"""
    A file to hold the dataset class to be used in training and running the model.
"""

import datetime
import json

from openai import OpenAI

import utils
import sqlite_db
import chroma_db
import user_pool
import potential_responses
import feature_extraction

"""
    An exception class for general dataset errors.
"""
class DatasetError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Dataset:
    def __init__(self, name, existing_dataset_name=None, init_chroma=False, use_openai_client=False, override_featurex_defaults=None):
        utils.load_env()

        self.name = name
        self.root_dataset_path = utils.fetch_env_var("ROOT_DATASET_PATH")
        self.has_chroma = False

        if use_openai_client:
            self.openai_client = OpenAI()
        if existing_dataset_name != None:
            self._init_from_existing(existing_dataset_name, init_chroma=init_chroma)
        else:
            self._init_from_scratch()

        self._num_text_samples = 5
        self._num_beliefs = 5
        self._belief_char_max = 200
        self._num_interests = 5
        self._skip_sub_ret_errors = False

        if override_featurex_defaults != None:
            if "num_text_samples" in override_featurex_defaults: 
                self._num_text_samples = override_featurex_defaults["num_text_samples"]
            if "num_beliefs" in override_featurex_defaults:
                self._num_beliefs = override_featurex_defaults["num_beliefs"]
            if "belief_char_max" in override_featurex_defaults:
                self._belief_char_max = override_featurex_defaults["belief_char_max"]
            if "num_interests" in override_featurex_defaults:
                self._num_interests = override_featurex_defaults["num_interests"]
            if "skip_sub_ret_errors" in  override_featurex_defaults:
                self._skip_sub_ret_errors = override_featurex_defaults["skip_sub_ret_errors"]
    
    """
        Initialize from an existing dataset in the format produced in the data module.
    """
    def _init_from_existing(self, existing_dataset_name, init_chroma=False):
        self.dataset_path = self.root_dataset_path + existing_dataset_name + "/"
        print(f"Initializing dataset {self.name} from existing dataset at {self.dataset_path}...")

        self.sqlite_db_path = self.dataset_path + "data.db"
        self.sqlite_db = sqlite_db.SqliteDB(self.sqlite_db_path)

        self.chroma_db_path = self.dataset_path + ".chroma"
        self.chroma_db = chroma_db.ChromaDB(self.chroma_db_path, create=init_chroma)

        self.username_list_path = self.dataset_path  + "usernames.json"
        usernames = utils.read_json(self.username_list_path)
        self.user_pool = user_pool.UserPool(self.name, usernames)
        if init_chroma:
            user_profiles = self.user_pool.fetch_all_user_profiles(sqlite_db=self.sqlite_db, load_submissions=True)
            
            user_dicts = [user_profile.get_sqlite_att_dict() for user_profile in user_profiles]
            self.chroma_db.embed_datatype("user_profile", user_dicts)

            for user_profile in user_profiles:
                user_post_dicts = [post.get_sqlite_att_dict() for post in user_profile.posts]
                self.chroma_db.embed_datatype("post", user_post_dicts)

                user_comment_dicts = [comment.get_sqlite_att_dict() for comment in user_profile.comments]
                self.chroma_db.embed_datatype("comment", user_comment_dicts)

                user_favorite_post_dicts = [post.get_sqlite_att_dict() for post in user_profile.favorite_posts]
                self.chroma_db.embed_datatype("post", user_favorite_post_dicts)

        self.prf_path = self.dataset_path  + "prf.json"
        prf = utils.read_json(self.prf_path)
        self.prf = potential_responses.PotentialResponseForest(self.name, prf)
        if init_chroma:
            all_items = self.prf.get_all_items()

            posts = [item.fetch_contents(sqlite_db=self.sqlite_db) for item in all_items if item.get_is_root()]
            post_dicts = [post.get_sqlite_att_dict() for post in posts]
            self.chroma_db.embed_datatype("post", post_dicts)

            comments = [item.fetch_contents(sqlite_db=self.sqlite_db) for item in all_items if not item.get_is_root()]
            comment_dicts = [comment.get_sqlite_att_dict() for comment in comments]
            self.chroma_db.embed_datatype("comment", comment_dicts)

            self.has_chroma = True

        print(f"Successfully initialized dataset {self.name} from existing dataset at {self.dataset_path}.")

    """
        Initialize a new dataset from scratch, with the given name.
    """
    def _init_from_scratch(self):
        self.dataset_path = self.root_dataset_path + self.name + "/"

        if utils.check_directory_exists(self.dataset_path):
            raise DatasetError(f"Error: Attempted to create dataset from scratch, at existing directory path {self.dataset_path}.")

        print(f"Initializing new dataset {self.name} at {self.dataset_path}...")

        utils.create_directory(self.dataset_path)

        empty_prf = []

        self.sqlite_db_path = self.dataset_path + "data.db"
        self.sqlite_db = sqlite_db.SqliteDB(self.sqlite_db_path, create=True)

        self.chroma_db_path = self.dataset_path + ".chroma"
        self.chroma_db = chroma_db.ChromaDB(self.chroma_db_path, create=True)
        self.has_chroma = True

        self.username_list_path = self.dataset_path + "usernames.json"
        utils.write_json([], self.username_list_path)
        self.user_pool = user_pool.UserPool(self.name, [])

        self.prf_path = self.dataset_path + "prf.json"
        utils.write_json([], self.prf_path)
        self.prf = potential_responses.PotentialResponseForest(self.name, [])

        print(f"Successfully initialized new dataset {self.name} at {self.dataset_path}.")

    def __str__(self):
        return f"""
            Dataset {self.name}
            {self.user_pool}
            {self.prf}
        """

    def get_name(self):
        return self.name

    def get_sqlite_db(self):
        return self.sqlite_db

    def get_initial_time(self):
        return self.initial_time
    
    def get_current_time(self):
        return self.current_time

    """
        Write the current username list to a JSON.
    """
    def write_current_username_list(self):
        current_usernames = self.user_pool.get_usernames()
        utils.write_json(current_usernames, self.username_list_path)

    """
        Write the current potential response forest to a JSON.
    """
    def write_current_prf(self):
        current_prf = self.prf.get_current_prf()
        utils.write_json(current_prf, self.prf_path)

    """
        Get the string representation of a given username.
    """
    def user_profile_str(self, username):
        user_profile = self.user_pool.fetch_user_profile(username, sqlite_db=self.sqlite_db, chroma_db=self.chroma_db)
        return str(user_profile)
    
    """
        Get the string representation of a potential response item, given its id.
    """
    def item_str(self, item_id):
        item = self.prf.get_item(item_id)
        item_contents = item.fetch_contents(sqlite_db=self.sqlite_db)
        return str(item_contents)

    """
        Get the string representation of a full branch of a potential response item, given its id.
    """
    def branch_str(self, item_id):
        branch = self.prf.get_branch(item_id)
        branch_content = [item.fetch_contents(sqlite_db=self.sqlite_db) for item in branch]
        contents  = f"Full branch of item {item_id}:" + "\n"
        for item_content in branch_content:
            contents += "\t" + str(item_content) + "\n"
        return contents

    """
        Add a set of users to the dataset, given a list of attribute dicts.
    """
    def add_users(self, user_dict_list, check_submission_history=False):
        try:
            username_list = [user_dict["username"] for user_dict in user_dict_list]

            print("Adding users")
            for username in username_list:
                print(username)
            print("to the dataset...")

            self.user_pool.add_usernames(username_list)

            print("Putting into sqlite...")
            self.sqlite_db.insert_user_profiles(user_dict_list, check_submission_history=check_submission_history) 

            if self.has_chroma:
                print("Generating embeddings...")
                self.chroma_db.embed_datatype("user_profile", user_dict_list)

            self.write_current_username_list()

            print("Successfully added users")
            for username in username_list:
                print(username)
            print("to the dataset.")

            return True
        except Exception as e:
            print(f"Error adding users to {self}:")
            print(e)
            return False

    """
        Remove a list of users from the dataset, given their usernames.
    """
    def remove_users(self, username_list, remove_posts=False, remove_comments=False):
        try:

            print("Removing users:")
            for username in username_list:
                print(username)
            if remove_posts:
                print("and all of their posts")
            if remove_comments:
                print("and all of their comments")
            print("from the dataset...")

            user_profiles = self.user_pool.fetch_some_user_profiles(username_list, self.sqlite_db)

            if remove_posts:
                for user_profile in user_profiles:
                    post_ids = user_profile.post_ids
                    self.remove_root_posts(post_ids)
            if remove_comments:
                for user_profile in user_profiles:
                    comment_ids = user_profile.comment_ids
                    self.remove_comments(comment_ids)

            print("Removing from sqlite...")
            self.sqlite_db.remove_items("userProfiles", username_list)

            if self.has_chroma:
                print("Removing embeddings...")
                self.chroma_db.remove_embeddings_for_datatype("user_profile", username_list)

            self.user_pool.remove_usernames(username_list)

            self.write_current_username_list()

            print("Successfully removed users:")
            for username in username_list:
                print(username)
            if remove_posts:
                print("and all of their posts")
            if remove_comments:
                print("and all of their comments")
            print("from the dataset.")

            return True
        except Exception as e:
            print("Error removing users from the dataset:")
            print(e)
            return False

    """
        Add a set of new root posts to the dataset, given a list of attribute dicts
    """
    def add_root_posts(self, post_dict_list):
        try:
            print("Adding root posts:")
            for post_dict in post_dict_list:
                print(post_dict["id"])
            print("to the dataset...")

            self.prf.add_roots([post_dict["id"] for post_dict in post_dict_list])

            print("Putting into sqlite...")
            self.sqlite_db.insert_posts(post_dict_list)

            if self.has_chroma:
                print("Generating embeddings...")
                self.chroma_db.embed_datatype("post", post_dict_list)

            self.write_current_prf()

            print("Successfully added root posts")
            for post_dict in post_dict_list:
                print(post_dict["id"])
            print("to the dataset.")

            return True
        except Exception as e:
            print("Error adding roots to {self}")
            print(e)
            return False

    """
        Remove a list of root posts from the dataset, given their ids.
    """
    def remove_root_posts(self, post_ids, update_author_profile=False):
        try:

            print("Removing root posts:")
            for post_id in post_ids:
                print(post_id)
            print("from the dataset...")

            all_kid_ids = []
            for post_id in post_ids:
                post = self.prf.get_item(post_id)
                kids = post.get_kids()
                kid_ids = [kid.get_id() for kid in kids]
                all_kid_ids = [*all_kid_ids, *kid_ids]
            self.remove_comments(all_kid_ids, update_author_profile=update_author_profile)
            
            if update_author_profile:
                author_post_map = {}
                for post_id in post_ids:
                    post = self.prf.get_item(post_id)
                    post_contents = post.fetch_contents(sqlite_db=self.sqlite_db)
                    author_username = post_contents.by
                    if author_username in author_post_map:
                        author_post_map[author_username].append(post_id)
                    else:
                        author_post_map[author_username] = [post_id]

                for username, user_post_ids in author_post_map.items():
                    self.sqlite_db.remove_post_ids_from_user(username, user_post_ids)

            print("Removing from sqlite...")
            self.sqlite_db.remove_items("posts", post_ids)

            if self.has_chroma:
                print("Removing embeddings...")
                self.chroma_db.remove_embeddings_for_datatype("post", post_ids)

            self.prf.remove_roots(post_ids)

            self.write_current_prf()

            print("Successfully removed root posts with ids:")
            for post_id in post_ids:
                print(post_id)
            print("from the dataset.")

            return True
        except Exception as e:
            print("Error removing root posts from the dataset:")
            print(e)
            return False

    """
        Add a list of leaf comments to the dataset, 
        given a list of dicts including both their attributes and a parent ID.
    """
    def add_leaf_comments(self, leaf_dict_list):
        try:
            print("Adding leaf comments:")
            for leaf_dict in leaf_dict_list:
                print(leaf_dict["id"])
            print("to the dataset...")

            for leaf_dict in leaf_dict_list:
                parent_id = leaf_dict["parent_id"]
                parent = self.prf.get_item(parent_id)
                parent.add_kid(leaf_dict["id"])

            print("Putting into sqlite...")
            self.sqlite_db.insert_comments(leaf_dict_list)

            if self.has_chroma:
                print("Generating embeddings...")
                self.chroma_db.embed_datatype("comment", leaf_dict_list)

            self.write_current_prf()

            print("Succesfully added leaf comments")
            for leaf_dict in leaf_dict_list:
                print(leaf_dict["id"])
            print("to the dataset.")

            return True
        except Exception as e:
            print("Error adding comments to dataset:")
            print(e)
            return False

    """
        Remove a list of comments from the dataset, and all of their descendants, given a list of ids.
        (passing in non-existing comment ids is chill here)
    """
    def remove_comments(self, comment_ids, update_author_profile=False):
        try:
            print("Removing comments:")
            for comment_id in comment_ids:
                print(comment_id)
            print("and all of their descendants from the dataset...")

            all_comments_to_remove = []

            for comment_id in comment_ids:
                try:
                    comment = self.prf.get_item(comment_id)
                except potential_responses.PotentialResponseForestError as e:
                    print(f"Attempted to remove comment with id {comment_id} which does not exist in potential response forest. Skipping...")
                    continue
                comment_and_descendants = [dec for dec in comment.get_flattened_descendants()]
                all_comments_to_remove = [*all_comments_to_remove, *comment_and_descendants]
            
            print("Full list of comments to be removed, including descendants:")
            for comment in all_comments_to_remove:
                print(comment.get_id())
            

            if update_author_profile:
                comment_contents = [comment.fetch_contents(sqlite_db=self.sqlite_db) for comment in all_comments_to_remove]

                author_comment_map = {}

                for comment in comment_contents:
                    author_username = comment.by
                    if author_username in author_comment_map:
                        author_comment_map[author_username].append(comment.id)
                    else:
                        author_comment_map[author_username] = [comment.id]
                
                for username, user_comment_ids in author_comment_map.items():
                    unique_comment_ids = list(set(user_comment_ids))
                    self.sqlite_db.remove_comment_ids_from_user(username, unique_comment_ids)

            all_comment_ids_to_remove = [comment.get_id() for comment in all_comments_to_remove]
            unique_comment_ids_to_remove = list(set(all_comment_ids_to_remove))

            print("Removing from sqlite...")
            self.sqlite_db.remove_items("comments", unique_comment_ids_to_remove)

            if self.has_chroma:
                print("Removing embeddings...")
                self.chroma_db.remove_embeddings_for_datatype("comment", unique_comment_ids_to_remove)

            self.prf.remove_items(comment_ids)

            self.write_current_prf()

            print("Successfully removed comments with ids:")
            for comment_id in comment_ids:
                print(comment_id)
            print("and all of their descendants from the dataset.")

            return True
        except Exception as e:
            print("Error removing leaf comments from the dataset:")
            print(e)
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
        print(f"Initializing dataset {self.name} for run...")

        print("Cleaning user pool...")
        self.user_pool.clean(self.sqlite_db, self.chroma_db)

        print("Cleaning potential response forest...")
        self.prf.clean(self.sqlite_db, self.chroma_db)

        #If no initial time is specified,
        #Find the time at which the latest root post was made, and set that at the initial time.
        if initial_time == None:
            print("Finding initial time...")
            root_post_times = self.prf.get_root_times(self.sqlite_db)
            try:
                latest_time = max(root_post_times)
            except ValueError as e:
                print("Error finding latest time among current roots, they are likely empty.")
                print("This dataset is not ready for a run. Returning...")
                return
            self.initial_time = latest_time + 1
        else:
            print("Initial time has been given.")
            self.initial_time = initial_time
        
        self.current_time = self.initial_time

        print(f"Initial time: {datetime.datetime.fromtimestamp(self.initial_time)}")

        print(f"Successfully initialized dataset {self.name} for run.")
        
    """
        Get a full list of current feature sets for the database, consisting of all combinations
        of active potential response branches and users
    """
    def get_all_current_feature_sets(self):
        print(f"Getting feature sets for time {self.current_time}")
        
        print(f"Activating potential response items prior to that time...")
        self.prf.activate_before_time(self.sqlite_db, self.current_time)

        users = self.user_pool.fetch_all_user_profiles(sqlite_db)
        print(f"Number of users: {len(users)}")

        all_pr_branches = self.prf.get_all_active_branches()

        print(f"Number of potential response branches: {len(all_pr_branches)}")

        feature_sets = []
        for user in users:
            for pr in all_pr_branches:
                #TODO: function to create final feature set
                feature_set = f"user: {user}, pr: {pr}"
                feature_sets.append(feature_set)

        print(f"Successfully got all current feature sets for time {self.current_time}.")
        print(f"Number of feature sets: {len(feature_sets)}")
        return feature_sets

    """
        Add to the misc json record for a given user profile in the user pool.
    """
    def add_misc_json_to_user_profile(self, username, dict_to_add):
        user_profile = self.user_pool.fetch_user_profile(username, sqlite_db=self.sqlite_db)
        
        #TODO: originally put misc json in as an empty list. this is dumb
        if isinstance(user_profile.misc_json, dict):
            new_misc_json = {**user_profile.misc_json, **dict_to_add}
        else:
            new_misc_json = dict_to_add

        update_dict = {"miscJson": json.dumps(new_misc_json)}
        self.sqlite_db.update_user_profile(username, update_dict)

    """
        Add to the misc json record for a given item in the PRF.
    """
    def add_misc_json_to_item(self, item_id, dict_to_add):
        item = self.prf.get_item(item_id)
        item_contents = item.fetch_contents(sqlite_db=self.sqlite_db)
        
        #TODO: originally put misc json in as an empty list. this is dumb
        if isinstance(item_contents.misc_json, dict):
            print(item_contents.misc_json)
            new_misc_json = {**item_contents.misc_json, **dict_to_add}
            print(new_misc_json)
        else:
            new_misc_json = dict_to_add
            
        update_dict = {"miscJson": json.dumps(new_misc_json)}
        if item.get_is_root():
            self.sqlite_db.update_post_record(item_id, update_dict)
        else:
            self.sqlite_db.update_comment_record(item_id, update_dict)

    """
        Populate the text samples record for a given username in the user pool.
    """
    def populate_text_samples(self, username):
        print(f"Populating text samples via LLM for user {username}...")
        user_profile = self.user_pool.fetch_user_profile(username, sqlite_db=self.sqlite_db, load_submissions=true)

        print("Generating...")
        text_samples = feature_extraction.get_text_samples(username, user_profile.comments, self._num_text_samples, self.openai_client, skip_sub_ret_errors=self._skip_sub_ret_errors)
        
        print("Putting into sqlite...")
        update_dict = {"textSamples": json.dumps(text_samples)}
        self.sqlite_db.update_user_profile(username, update_dict)

        print("Updating embeddings...")
        update_dict = {"text_samples": text_samples, "username": username}
        self.chroma_db.update_embeddings_for_datatype("user_profile", [update_dict], atts=["text_samples"])

        print(f"Successfully populated text samples via LLM for user {username}.")

    """
        Populate the beliefs record for a given user in the user pool.
    """
    def populate_beliefs(self, username):
        print(f"Populating beliefs via LLM for user {username}...")
        user_profile = self.user_pool.fetch_user_profile(username, sqlite_db=self.sqlite_db, load_submissions=True)

        print("Generating...")
        beliefs = feature_extraction.get_beliefs(username, user_profile.submissions, self._num_beliefs, self._belief_char_max, self.openai_client, skip_sub_ret_errors=self._skip_sub_ret_errors)

        print("Putting into sqlite...")        
        update_dict = {"beliefs": json.dumps(beliefs)}
        self.sqlite_db.update_user_profile(username, update_dict)

        print("Updating embeddings...")
        update_dict = {"beliefs": beliefs, "username": username}
        self.chroma_db.update_embeddings_for_datatype("user_profile", [update_dict], atts=["beliefs"])

        print(f"Successfully populated beliefs via LLM for user {username}.")

    """
        Populate the interests record for a given user in the user pool.
    """
    def populate_interests(self, username):
        print(f"Populating interests via LLM for user {username}...")
        user_profile = self.user_pool.fetch_user_profile(username, sqlite_db=self.sqlite_db, load_submissions=True)

        print("Generating...")
        interests = feature_extraction.get_interests(username, user_profile.submissions, self._num_interests, self.openai_client, skip_sub_ret_errors=self._skip_sub_ret_errors)

        print("Putting into sqlite...")        
        update_dict = {"interests": json.dumps(interests)}
        self.sqlite_db.update_user_profile(username, update_dict)

        print("Updating embeddings...")
        update_dict = {"interests": interests, "username": username}
        self.chroma_db.update_embeddings_for_datatype("user_profile", [update_dict], atts=["interests"])

        print(f"Successfully populated interests via LLM for user {username}.")