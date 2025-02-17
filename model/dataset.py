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
import potential_responses
import feature_extraction

"""
    An exception class for general dataset errors.
"""
class DatasetError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Dataset:
    def __init__(self, name, existing_dataset_name=None, init_chroma=False, use_openai_client=False, verbose=False):

        self.name = name
        self.verbose = verbose

        if use_openai_client:
            self.openai_client = OpenAI()
        if existing_dataset_name != None:
            self._init_from_existing(existing_dataset_name, init_chroma=init_chroma)
        else:
            self._init_from_scratch()
        
        self._submission_history_max = {
            "posts": 10,
            "comments": 10, 
            "favorite_posts": 10
        }

        self.text_atts = [
            {"datatype": "user_profile", "name": "about", "list": False},
            {"datatype": "post", "name": "title", "list": False},
            {"datatype": "post", "name": "text", "list": False},
            {"datatype": "post", "name": "url_content", "list": False},
            {"datatype": "comment", "name": "text", "list": False}
        ]
    
    def _print(self, s):
        if self.verbose:
            print(s)

    def set_verbose(self, verbose):
        self.verbose = verbose

    """
        Initialize from an existing dataset in the format produced in the data module.
    """
    def _init_from_existing(self, existing_dataset_name, init_chroma=False):
        self.dataset_path = utils.get_dataset_path(existing_dataset_name) + "/"
        self._print(f"Initializing dataset {self.name} from existing dataset at {self.dataset_path}...")

        self.sqlite_db_path = self.dataset_path + "data.db"
        self.sqlite_db = sqlite_db.SqliteDB(self.sqlite_db_path)

        self.chroma_db_path = self.dataset_path + ".chroma"
        self.has_chroma = utils.check_directory_exists(self.chroma_db_path)

        if init_chroma and self.has_chroma:
            raise DatasetError(f"Error: attempted to initialize a chroma db for a dataset that already has one.")

        if init_chroma or self.has_chroma: 
            self.chroma_db = chroma_db.ChromaDB(self.chroma_db_path, create=init_chroma)

        self.username_list_path = self.dataset_path  + "usernames.json"
        usernames = utils.read_json(self.username_list_path)
        self.user_pool = user_pool.UserPool(self.name, usernames)

        self.prf_path = self.dataset_path  + "prf.json"
        prf = utils.read_json(self.prf_path)
        self.prf = potential_responses.PotentialResponseForest(self.name, prf)

        if init_chroma:
            self._print(f"Initializing chroma db for dataset {self.name} from existing dataset at {self.dataset_path}...")

            self._print("Cleaning user pool...")
            self.user_pool.clean(sqlite_db=self.sqlite_db, verbose=self.verbose)

            self._print("Fetching user profiles from sqlite to be embedded...")
            user_profiles = self.user_pool.fetch_all_user_profiles(sqlite_db=self.sqlite_db, load_submissions=True, verbose=self.verbose)
            
            user_dicts = [user_profile.get_sqlite_att_dict() for user_profile in user_profiles]
            self._print("Embedding user profiles...")
            self.chroma_db.embed_datatype("user_profile", user_dicts)

            self._print("Embedding submission histories for user profiles...")
            for user_profile in user_profiles:
                self._print("Embedding post history...")
                user_post_dicts = [post.get_sqlite_att_dict() for post in user_profile.posts]
                self.chroma_db.embed_datatype("post", user_post_dicts)

                self._print("Embedding comment history...")
                user_comment_dicts = [comment.get_sqlite_att_dict() for comment in user_profile.comments]
                self.chroma_db.embed_datatype("comment", user_comment_dicts)

                self._print("Embedding favorite posts...")
                user_favorite_post_dicts = [post.get_sqlite_att_dict() for post in user_profile.favorite_posts]
                self.chroma_db.embed_datatype("post", user_favorite_post_dicts)

            self._print("Cleaning potential response forest...")
            self.prf.clean(sqlite_db=self.sqlite_db, verbose=self.verbose)

            all_items = self.prf.get_all_items()

            self._print("Fetching root posts from sqlite to be embedded...")
            posts = [item.fetch_contents(sqlite_db=self.sqlite_db, verbose=self.verbose) for item in all_items if item.get_is_root()]
            post_dicts = [post.get_sqlite_att_dict() for post in posts]

            self._print("Embedding root posts...")
            self.chroma_db.embed_datatype("post", post_dicts)

            self._print("Fetching comments from sqlite to be embedded...")
            comments = [item.fetch_contents(sqlite_db=self.sqlite_db) for item in all_items if not item.get_is_root()]
            comment_dicts = [comment.get_sqlite_att_dict() for comment in comments]

            self._print("Embedding comments...")
            self.chroma_db.embed_datatype("comment", comment_dicts)

            self._print(f"Successfully initialized chroma db for dataset {self.name} from existing dataset at {self.dataset_path}")
            self.has_chroma = True

        self._print(f"Successfully initialized dataset {self.name} from existing dataset at {self.dataset_path}.")

    """
        Initialize a new dataset from scratch, with the given name.
    """
    def _init_from_scratch(self):
        self.dataset_path = utils.get_dataset_path(self.name) + "/"

        if utils.check_directory_exists(self.dataset_path):
            raise DatasetError(f"Error: Attempted to create dataset from scratch, at existing directory path {self.dataset_path}.")

        self._print(f"Initializing new dataset {self.name} at {self.dataset_path}...")

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

        self._print(f"Successfully initialized new dataset {self.name} at {self.dataset_path}.")

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

            self._print("Adding users")
            for username in username_list:
                self._print(username)
            self._print("to the dataset...")

            self.user_pool.add_usernames(username_list)

            self._print("Putting into sqlite...")
            self.sqlite_db.insert_user_profiles(user_dict_list, check_submission_history=check_submission_history) 

            if self.has_chroma:
                self._print("Generating embeddings...")
                self.chroma_db.embed_datatype("user_profile", user_dict_list)

            self.write_current_username_list()

            self._print("Successfully added users")
            for username in username_list:
                self._print(username)
            self._print("to the dataset.")

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

            self._print("Removing users:")
            for username in username_list:
                self._print(username)
            if remove_posts:
                self._print("and all of their posts")
            if remove_comments:
                self._print("and all of their comments")
            self._print("from the dataset...")

            user_profiles = self.user_pool.fetch_some_user_profiles(username_list, self.sqlite_db)

            if remove_posts:
                for user_profile in user_profiles:
                    post_ids = user_profile.post_ids
                    self.remove_root_posts(post_ids)
            if remove_comments:
                for user_profile in user_profiles:
                    comment_ids = user_profile.comment_ids
                    self.remove_comments(comment_ids)

            self._print("Removing from sqlite...")
            self.sqlite_db.remove_items("userProfiles", username_list)

            if self.has_chroma:
                self._print("Removing embeddings...")
                self.chroma_db.remove_embeddings_for_datatype("user_profile", username_list)

            self.user_pool.remove_usernames(username_list)

            self.write_current_username_list()

            self._print("Successfully removed users:")
            for username in username_list:
                self._print(username)
            if remove_posts:
                self._print("and all of their posts")
            if remove_comments:
                self._print("and all of their comments")
            self._print("from the dataset.")

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
            self._print("Adding root posts:")
            for post_dict in post_dict_list:
                self._print(post_dict["id"])
            self._print("to the dataset...")

            self.prf.add_roots([post_dict["id"] for post_dict in post_dict_list])

            self._print("Putting into sqlite...")
            self.sqlite_db.insert_posts(post_dict_list)

            if self.has_chroma:
                self._print("Generating embeddings...")
                self.chroma_db.embed_datatype("post", post_dict_list)

            self.write_current_prf()

            self._print("Successfully added root posts")
            for post_dict in post_dict_list:
                self._print(post_dict["id"])
            self._print("to the dataset.")

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

            self._print("Removing from sqlite...")
            self.sqlite_db.remove_items("posts", post_ids)

            if self.has_chroma:
                self._print("Removing embeddings...")
                self.chroma_db.remove_embeddings_for_datatype("post", post_ids)

            self.prf.remove_roots(post_ids)

            self.write_current_prf()

            self._print("Successfully removed root posts with ids:")
            for post_id in post_ids:
                self._print(post_id)
            self._print("from the dataset.")

            return True
        except Exception as e:
            print("Error removing root posts from the dataset:")
            print(e)
            return False

    """
        Add a list of leaf comments to the dataset, 
        given a list of dicts including their attributes.
    """
    def add_leaf_comments(self, leaf_dict_list):
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
            self.sqlite_db.insert_comments(leaf_dict_list)

            if self.has_chroma:
                self._print("Generating embeddings...")
                self.chroma_db.embed_datatype("comment", leaf_dict_list)

            self.write_current_prf()

            self._print("Succesfully added leaf comments")
            for leaf_dict in leaf_dict_list:
                self._print(leaf_dict["id"])
            self._print("to the dataset.")

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

            self._print("Removing from sqlite...")
            self.sqlite_db.remove_items("comments", unique_comment_ids_to_remove)

            if self.has_chroma:
                self._print("Removing embeddings...")
                self.chroma_db.remove_embeddings_for_datatype("comment", unique_comment_ids_to_remove)

            self.prf.remove_items(comment_ids)

            self.write_current_prf()

            self._print("Successfully removed comments with ids:")
            for comment_id in comment_ids:
                self._print(comment_id)
            self._print("and all of their descendants from the dataset.")

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
        self._print(f"Initializing dataset {self.name} for run...")

        self._print("Cleaning user pool...")
        self.user_pool.clean(sqlite_db=self.sqlite_db, chroma_db=self.chroma_db)

        self._print("Cleaning potential response forest...")
        self.prf.clean(sqlite_db=self.sqlite_db, chroma_db=self.chroma_db)

        #If no initial time is specified,
        #Find the time at which the latest root post was made, and set that at the initial time.
        if initial_time == None:
            self._print("Finding initial time...")
            root_post_times = self.prf.get_root_times(self.sqlite_db)
            try:
                latest_time = max(root_post_times)
            except ValueError as e:
                print("Error finding latest time among current roots, they are likely empty.")
                print("This dataset is not ready for a run. Returning...")
                return
            self.initial_time = latest_time + 1
        else:
            self._print("Initial time has been given.")
            self.initial_time = initial_time
        
        self.current_time = self.initial_time

        self._print(f"Initial time: {datetime.datetime.fromtimestamp(self.initial_time)}")

        self._print(f"Successfully initialized dataset {self.name} for run.")
        
    """
        Get a full list of current feature sets for the database, consisting of all combinations
        of active potential response branches and users
    """
    def get_all_current_feature_sets(self):
        self._print(f"Getting feature sets for time {self.current_time}")
        
        self._print(f"Activating potential response items prior to that time...")
        self.prf.activate_before_time(self.sqlite_db, self.current_time)

        users = self.user_pool.fetch_all_user_profiles(sqlite_db)
        self._print(f"Number of users: {len(users)}")

        all_pr_branches = self.prf.get_all_active_branches()

        self._print(f"Number of potential response branches: {len(all_pr_branches)}")

        feature_sets = []
        for user in users:
            for pr in all_pr_branches:
                #TODO: function to create final feature set
                feature_set = f"user: {user}, pr: {pr}"
                feature_sets.append(feature_set)

        self._print(f"Successfully got all current feature sets for time {self.current_time}.")
        self._print(f"Number of feature sets: {len(feature_sets)}")
        return feature_sets


    """
        Summarize the url content of a given post in the dataset, given its sqlite attributes dict.
    """
    def summarize_url_content(self, post_dict):
        self._print(f"Summarizing url content for post of id {post_dict['id']}")

        self._print("Generating...")
        summary = feature_extraction.summarize_url_content(post_dict["url_content"], self._url_content_char_max, self.openai_client)

        self._print("Putting into sqlite...")
        update_dict = {"url_content": summary}
        self.sqlite_db.update_post_record(post_dict["id"], update_dict)

        self._print("Updating embeddings...")
        update_dict = {"url_content": summary, "id": post_dict["id"]}

        self._print(f"Successfully summarized url content via LLM for post {post_dict['id']}")

    """
        Populate the text samples record for a given username in the user pool.
    """
    def populate_text_samples(self, username):
        self._print(f"Populating text samples via LLM for user {username}...")
        user_profile = self.user_pool.fetch_user_profile(username, sqlite_db=self.sqlite_db, load_submissions=True)

        self._print("Generating...")
        text_samples = feature_extraction.get_text_samples(username, user_profile.comments, self._num_text_samples, self.openai_client, self._submission_history_max, skip_sub_ret_errors=self._skip_sub_ret_errors)
        
        self._print("Putting into sqlite...")
        update_dict = {"textSamples": json.dumps(text_samples)}
        self.sqlite_db.update_user_profile(username, update_dict)

        self._print("Updating embeddings...")
        update_dict = {"text_samples": text_samples, "username": username}
        self.chroma_db.update_embeddings_for_datatype("user_profile", [update_dict], atts=["text_samples"])

        self._print(f"Successfully populated text samples via LLM for user {username}.")

    """
        Populate the beliefs record for a given user in the user pool.
    """
    def populate_beliefs(self, username):
        self._print(f"Populating beliefs via LLM for user {username}...")
        user_profile = self.user_pool.fetch_user_profile(username, sqlite_db=self.sqlite_db, load_submissions=True)

        self._print("Generating...")
        beliefs = feature_extraction.get_beliefs(username, user_profile.submissions, self._num_beliefs, self._belief_char_max, self.openai_client, self._submission_history_max, skip_sub_ret_errors=self._skip_sub_ret_errors)

        self._print("Putting into sqlite...")        
        update_dict = {"beliefs": json.dumps(beliefs)}
        self.sqlite_db.update_user_profile(username, update_dict)

        self._print("Updating embeddings...")
        update_dict = {"beliefs": beliefs, "username": username}
        self.chroma_db.update_embeddings_for_datatype("user_profile", [update_dict], atts=["beliefs"])

        self._print(f"Successfully populated beliefs via LLM for user {username}.")

    """
        Populate the interests record for a given user in the user pool.
    """
    def populate_interests(self, username):
        self._print(f"Populating interests via LLM for user {username}...")
        user_profile = self.user_pool.fetch_user_profile(username, sqlite_db=self.sqlite_db, load_submissions=True)

        self._print("Generating...")
        interests = feature_extraction.get_interests(username, user_profile.submissions, self._num_interests, self.openai_client, self._submission_history_max, skip_sub_ret_errors=self._skip_sub_ret_errors)

        self._print("Putting into sqlite...")        
        update_dict = {"interests": json.dumps(interests)}
        self.sqlite_db.update_user_profile(username, update_dict)

        self._print("Updating embeddings...")
        update_dict = {"interests": interests, "username": username}
        self.chroma_db.update_embeddings_for_datatype("user_profile", [update_dict], atts=["interests"])

        self._print(f"Successfully populated interests via LLM for user {username}.")

    """
        Get a cost estimate for running feature extraction on a given user.
    """
    def openai_user_featurex_cost_estimate(self, username):
        print(f"Getting cost estimate for running feature extraction on user {username}...")
        GPT4O_INPUT_TOKEN_RATE = 2.5 / 1000000
        GPT4O_OUTPUT_TOKEN_RATE = 10 / 1000000

        user_profile = self.user_pool.fetch_user_profile(username, sqlite_db=self.sqlite_db, load_submissions=True)
        
        text_samples = feature_extraction.get_text_samples(username, user_profile.comments, self._num_text_samples, self.openai_client, self._submission_history_max, skip_sub_ret_errors=self._skip_sub_ret_errors, token_estimate=True)
        beliefs = feature_extraction.get_beliefs(username, user_profile.submissions, self._num_beliefs, self._belief_char_max, self.openai_client, self._submission_history_max, skip_sub_ret_errors=self._skip_sub_ret_errors, token_estimate=True)
        interests = feature_extraction.get_interests(username, user_profile.submissions, self._num_interests, self.openai_client, self._submission_history_max, skip_sub_ret_errors=self._skip_sub_ret_errors, token_estimate=True)

        total_input_tokens = text_samples["input"] + beliefs["input"] + interests["input"]
        estimated_output_tokens = text_samples["output"] + beliefs["output"] + interests["output"]

        total_input_cost = total_input_tokens * GPT4O_INPUT_TOKEN_RATE
        estimated_output_cost = estimated_output_tokens * GPT4O_OUTPUT_TOKEN_RATE

        estimated_total_cost = total_input_cost + estimated_output_cost

        print(f"Total input tokens: {total_input_tokens}")
        print(f"Associated cost: ${total_input_cost}")
        print(f"Total estimated output tokens: {estimated_output_tokens}")
        print(f"Associated cost: ${estimated_output_cost}")
        print(f"Estimated total cost: ${estimated_total_cost}")

        return estimated_total_cost
    
    """
        Get a cost estimate for running feature extraction on a given post.
    """
    def openai_post_summarization_cost_estimate(self, post_dict):
        print(f"Getting cost estimate for summarizing post with id {post_dict['id']}...")
        GPT4O_INPUT_TOKEN_RATE = 2.5 / 1000000
        GPT4O_OUTPUT_TOKEN_RATE = 10 / 1000000

        summary = feature_extraction.summarize_url_content(post_dict["url_content"], self._url_content_char_max, self.openai_client, token_estimate=True)

        total_input_tokens = summary["input"]
        estimated_output_tokens = summary["output"]

        total_input_cost = total_input_tokens * GPT4O_INPUT_TOKEN_RATE
        estimated_output_cost = estimated_output_tokens * GPT4O_OUTPUT_TOKEN_RATE
        estimated_total_cost = total_input_cost + estimated_output_cost

        print(f"Total input tokens: {total_input_tokens}")
        print(f"Associated cost: ${total_input_cost}")
        print(f"Total estimated output tokens: {estimated_output_tokens}")
        print(f"Associated cost: ${estimated_output_cost}")
        print(f"Estimated total cost: ${estimated_total_cost}")

        return estimated_total_cost

    """
        Get a full cost estimate for feature extraction with OpenAI on this dataset.
    """
    def full_openai_featurex_cost_estimate(self):
        print(f"Getting cost estimate for OpenAI feature extraction on dataset...")
        estimated_total_cost = 0

        real_usernames = [user.username for user in self.user_pool.fetch_all_user_profiles(sqlite_db=self.sqlite_db) if user.user_class == "real"]
        for username in real_usernames:
            estimated_total_cost += self.openai_user_featurex_cost_estimate(username)

        root_post_dicts = [root.fetch_contents(sqlite_db=self.sqlite_db).get_sqlite_att_dict() for root in self.prf.get_roots()]
        users = self.user_pool.fetch_all_user_profiles(sqlite_db=self.sqlite_db, load_submissions=True)
        user_post_dicts = functools.reduce(lambda acc, i: [*acc, *i], [[post.get_sqlite_att_dict() for post in user.posts] for user in users], [])
        all_post_dicts = [*root_post_dicts, *[post for post in user_post_dicts if not (post in root_post_dicts)]]

        for post_dict in all_post_dicts:
            estimated_total_cost += self.openai_post_summarization_cost_estimate(post_dict)

        print(f"Estimated total cost of OpenAI feature extraction on dataset: ${estimated_total_cost}.")
        return estimated_total_cost


    """
        Get a cost estimate for creating embeddings for a list of dicts.
    """
    def ce_of_embedding_attribute(self, datatype, att, is_list_att, dict_list):
        if is_list_att:
            flattened = functools.reduce(lambda acc, d: [*acc, *[{"doc": list_att_item, "query_att": {"query_att": d[id_att]}, "id": uuid.uuid4()} for list_att_item in d[att] if list_att_item != ""]], dict_list, [])
            documents = [d["doc"] for d in flattened]
        else:
            dict_list = [d for d in dict_list if d[att] != ""]
            documents = [d[att] for d in dict_list]
        
        OPENAI_EMBEDDING_MODEL_RATES= {
            "text-embedding-3-small": 0.02 / 1000000,
            "text-embedding-3-large": 0.13 / 1000000
        }

        embedding_model = utils.fetch_env_var("EMBEDDING_MODEL")

        rate = OPENAI_EMBEDDING_MODEL_RATES[embedding_model]

        total_cost = 0
        for doc in documents:
            total_cost += rate * utils.get_openai_token_estimate(doc, embedding_model)
        
        print(f"Total cost of embedding {datatype}_{att}: ${total_cost}")
        return total_cost

    """
        Get a cost estimate for creating embeddings for a list of dicts representing one of the three datatypes
    """
    def ce_of_embedding_datatype(self, datatype, dict_list):
        datatype_atts = [att for att in self.text_atts if att["datatype"] == datatype]
        total_cost = 0
        for att in datatype_atts:
            total_cost += self.ce_of_embedding_attribute(att["datatype"], att["name"], att["list"], dict_list)

        print(f"Total cost of embedding {datatype}: ${total_cost}")
        return total_cost

    """
        Get a cost estimate for creating embeddings for this entire dataset.
    """
    def ce_embedding_dataset(self):
        self.user_pool.clean(sqlite_db=self.sqlite_db, skip_submission_errors=True)

        self.prf.clean(sqlite_db=self.sqlite_db)

        total_cost = 0

        user_profiles = self.user_pool.fetch_all_user_profiles(sqlite_db=self.sqlite_db, load_submissions=True, skip_submission_errors=True)
            
        user_dicts = [user_profile.get_sqlite_att_dict() for user_profile in user_profiles]
        total_cost += self.ce_of_embedding_datatype("user_profile", user_dicts)

        for user_profile in user_profiles:
            user_post_dicts = [post.get_sqlite_att_dict() for post in user_profile.posts]
            total_cost += self.ce_of_embedding_datatype("post", user_post_dicts)

            user_comment_dicts = [comment.get_sqlite_att_dict() for comment in user_profile.comments]
            total_cost += self.ce_of_embedding_datatype("comment", user_comment_dicts)

            user_favorite_post_dicts = [post.get_sqlite_att_dict() for post in user_profile.favorite_posts]
            total_cost += self.ce_of_embedding_datatype("post", user_favorite_post_dicts)

        all_items = self.prf.get_all_items()

        posts = [item.fetch_contents(sqlite_db=self.sqlite_db) for item in all_items if item.get_is_root()]
        post_dicts = [post.get_sqlite_att_dict() for post in posts]
        total_cost += self.ce_of_embedding_datatype("post", post_dicts)

        comments = [item.fetch_contents(sqlite_db=self.sqlite_db) for item in all_items if not item.get_is_root()]
        comment_dicts = [comment.get_sqlite_att_dict() for comment in comments]
        total_cost += self.ce_of_embedding_datatype("comment", comment_dicts)

        print(f"Total cost of generating embeddings for this dataset: ${total_cost}")


    """
        Run full feature extraction on a given user in the user pool.
    """
    def featurex_user(self, username):
        self._print(f"Extracting features from user {username}...")

        self.populate_text_samples(username)
        self.populate_beliefs(username)
        self.populate_interests(username)

        self._print(f"Successfully extracted features from user {username}.")

    """
        Run full feature extraction on all real users in the user pool.
    """
    def featurex_user_pool(self):
        real_usernames = [user.username for user in self.user_pool.fetch_all_user_profiles(sqlite_db=sqlite_db) if user.user_class == "real"]
        for username in real_usernames:
            self.featurex_user(username)
    
    """
        Summarize the url content for all posts in the dataset.
    """ 
    def summarize_all_posts(self):
        self._print(f"Summarizing URL contents for all posts in the dataset...")

        root_post_dicts = [root.fetch_contents(sqlite_db=self.sqlite_db).get_sqlite_att_dict() for root in self.prf.get_roots()]
        users = self.user_pool.fetch_all_user_profiles(sqlite_db=sqlite_db, load_submissions=True)
        user_post_dicts = functools.reduce(lambda acc, i: [*acc, *i], [[post.get_sqlite_att_dict() for post in user.posts] for user in users], [])
        all_post_dicts = [*root_post_dicts, *[post for post in user_post_dicts if not (post in root_post_dicts)]]

        for post_dict in all_post_dicts:
            self.summarize_url_content(post_dict)
            
        self._print(f"Successfully summarized URL contents for all posts in the dataset.")
    
    """
        Run full OpenAI feature extraction on this dataset.
    """
    def full_featurex(self):
        self._print(f"Running full OpenAI feature extraction on the dataset...")
        self.featurex_user_pool()
        self.summarize_all_posts()
        self._print(f"Successfully ran full OpenAI feature extraction on the dataset.")

