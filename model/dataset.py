"""
    A file to hold the dataset class to be used in training and running the model.
"""

import datetime

import utils
import sqlite_db
import user_pool
import potential_responses


class Dataset:
    def __init__(self, name, existing_dataset_name=None):
        self.name = name
        if existing_dataset_name != None:
            self._init_from_existing(existing_dataset_name)
    
    """
        Initialize from an existing dataset in the format produced in the data module.
    """
    def _init_from_existing(self, existing_dataset_name):
        root_dataset_path = utils.fetch_env_var("ROOT_DATASET_PATH")
        self.dataset_path = root_dataset_path + existing_dataset_name + "/"
        self.db_path = self.dataset_path + "data.db"
        self.username_list_path = self.dataset_path  + "usernames.json"
        self.prf_path = self.dataset_path  + "contentStringLists.json"

        self.sqlite_db = sqlite_db.SqliteDB(self.db_path)


        usernames = utils.read_json(self.username_list_path)
        prf = utils.read_json(self.prf_path)

        self.user_pool = user_pool.UserPool(self.name, existing_username_list=usernames)
        self.prf = potential_responses.PotentialResponseForest(self.name, existing_prf=prf)

    def __str__(self):
        return f"""
            dataset {self.name}
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
        Add a set of users to the dataset, given a list of attribute dicts.
    """
    def add_users(self, user_dict_list, check_submission_history=False):
        try:
            username_list = [user_dict["username"] for user_dict in user_dict_list]
            self.user_pool.add_usernames(username_list)
            self.sqlite_db.insert_user_profiles(user_dict_list, check_submission_history=check_submission_history)
            self.write_current_username_list()

            print("Successfully added users")
            [print(user_dict["username"]) for user_dict in user_dict_list]
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
            user_profiles = self.user_pool.fetch_some_user_profiles(username_list, self.sqlite_db)

            if remove_posts:
                for user_profile in user_profiles:
                    post_ids = user_profile.post_ids
                    self.remove_root_posts(post_ids)
            if remove_comments:
                for user_profile in user_profiles:
                    comment_ids = user_profile.comment_ids
                    self.remove_leaf_comments(comment_ids)

            self.sqlite_db.remove_items("userProfiles", username_list)

            self.user_pool.remove_usernames(username_list)

            self.write_current_username_list()

            print("Successfully removed users:")
            [print(username) for username in username_list]
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
            self.prf.add_roots([post_dict["id"] for post_dict in post_dict_list])
            self.sqlite_db.insert_posts(post_dict_list)
            self.write_current_prf()

            print("Successfully added root posts")
            [print(post_dict["id"]) for post_dict in post_dict_list]
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

            all_kid_ids = []
            for post_id in post_ids:
                post = self.prf.get_item(post_id)
                kids = post.get_kids()
                kid_ids = [kid.get_id() for kid in kids]
                all_kid_ids = [*all_kid_ids, *kid_ids]
            self.remove_leaf_comments(all_kid_ids, update_author_profile=update_author_profile)
            
            if update_author_profile:
                author_post_map = {}
                for post_id in post_ids:
                    post = self.prf.get_item(post_id)
                    post_contents = post.fetch_contents(self.sqlite_db)
                    author_username = post_contents.by
                    if author_username in author_post_map:
                        author_post_map[author_username].append(post_id)
                    else:
                        author_post_map[author_username] = [post_id]

                for username, user_post_ids in author_post_map.items():
                    self.sqlite_db.remove_post_ids_from_user(username, user_post_ids)

            self.sqlite_db.remove_items("posts", post_ids)

            self.prf.remove_roots(post_ids)

            self.write_current_prf()

            print("Successfully removed root posts with ids:")
            [print(post_id) for post_id in post_ids]
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
            for leaf_dict in leaf_dict_list:
                parent_id = leaf_dict["parent_id"]
                parent = self.prf.get_item(parent_id)
                parent.add_kid(leaf_dict["id"])
            self.sqlite_db.insert_comments(leaf_dict_list)
            self.write_current_prf()

            print("Succesfully added leaf comments")
            [print(leaf_dict["id"]) for leaf_dict in leaf_dict_list]
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
    def remove_leaf_comments(self, comment_ids, update_author_profile=False):
        try:
            all_comments_to_remove = []

            for comment_id in comment_ids:
                try:
                    comment = self.prf.get_item(comment_id)
                except potential_responses.PotentialResponseForestError as e:
                    print(f"Attempted to remove comment with id {comment_id} which does not exist in potential response forest. Skipping...")
                    continue
                comment_and_descendants = [dec for dec in comment.get_flattened_descendants()]
                all_comments_to_remove = [*all_comments_to_remove, *comment_and_descendants]
            
            if update_author_profile:
                comment_contents = [comment.fetch_contents(self.sqlite_db) for comment in all_comments_to_remove]

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
            self.sqlite_db.remove_items("comments", unique_comment_ids_to_remove)

            self.prf.remove_items(comment_ids)

            self.write_current_prf()

            print("Successfully removed leaf comments with ids:")
            [print(comment_id) for comment_id in comment_ids]
            print("from the dataset.")

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
        self.user_pool.clean(self.sqlite_db)

        print("Cleaning potential response forest...")
        self.prf.clean(self.sqlite_db)

        #If no initial time is specified,
        #Find the time at which the latest root post was made, and set that at the initial time.
        if initial_time == None:
            print("Finding initial time...")
            root_post_times = self.prf.get_root_times(self.sqlite_db)
            latest_time = max(root_post_times)
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