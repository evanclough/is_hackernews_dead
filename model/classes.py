"""
    The classes used to represent the three root datatypes, 
    and the content string abstraction.
"""

import utils
import sqlite_utils

import datetime
import json
import operator
import functools

"""
    A class to represent user profiles, to be used
    throughout training and running of the models.
"""
class UserProfile:
    def __init__(self, sqlite_row=None, raw_atts_dict=None):
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'
        if sqlite_row != None:
            self._init_from_sqlite(sqlite_row)
        if raw_atts_dict != None:
            self._init_from_raw_atts(raw_atts_dict)

    """
        Initialize the class from a row in the sqlite database.
    """
    def _init_from_sqlite(self, sqlite_row):
        self.username =  sqlite_row[0]
        self.about =  sqlite_row[1]
        self.karma = sqlite_row[2]
        self.created = int(sqlite_row[3])
        self.user_class = sqlite_row[4]
        self.post_ids = json.loads(sqlite_row[5])
        self.comment_ids = json.loads(sqlite_row[6])
        self.favorite_post_ids = json.loads(sqlite_row[7])
        self.text_samples = json.loads(sqlite_row[8])
        self.interests = json.loads(sqlite_row[9])
        self.beliefs = json.loads(sqlite_row[10])
        self.misc_json = json.loads(sqlite_row[11])

    """
        Initialize the class from a raw dictionary of attributes.
    """
    def _init_from_raw_atts(self, raw_atts_dict):
        self.username = raw_atts_dict["username"]
        self.about = raw_atts_dict["about"]
        self.karma = raw_atts_dict["karma"]
        self.created = int(raw_atts_dict["created"])
        self.user_class = raw_atts_dict["user_class"]
        self.post_ids = raw_atts_dict["post_ids"]
        self.comment_ids = raw_atts_dict["comment_ids"]
        self.favorite_post_ids = raw_atts_dict["favorite_post_ids"]
        self.text_samples = raw_atts_dict["text_samples"]
        self.interests = raw_atts_dict["interests"]
        self.beliefs = raw_atts_dict["beliefs"]
        self.misc_json = raw_atts_dict["misc_json"]

    def __str__(self):
        contents = "user:\n"
        contents += f"""
            username: {self.username}
            about: {self.about}
            created: {self.created}
            num posts: {len(self.post_ids)}
            num comments: {len(self.comment_ids)}
            text samples: {functools.reduce(lambda c, s: c + s, self.text_samples, '')}
            interests: {functools.reduce(lambda c, s: c + s, self.interests, '')}
            beliefs: {functools.reduce(lambda c, s: c + s, self.beliefs, '')}
        """
        return str(f"user {self.username}")


    """
        Check this user profile to see whether or not it contains everything necessary
        in creation of a full feature set.
    """
    def check(self, sqlite_cursor):
        if self._DEBUG_IGNORE_CHECK: 
            return True
        
        #check each post, comment, and favorite id to make sure its in the database
        for post_id in self.post_ids:
            post = sqlite_utils.get_post(sqlite_cursor, post_id)
            if post == None:
                print(f"{self} fails check, as post {post_id} in their history fails check.")
                return False
        
        for comment_id in self.comment_ids:
            comment = sqlite_utils.get_comment(sqlite_cursor, comment_id)
            if comment == None:
                print(f"{self} fails check, as comment {comment_id} in their history fails check.")
                return False

        for fav_post_id in self.favorite_post_ids:
            fav_post = sqlite_utils.get_post(sqlite_cursor, fav_post_id)
            if fav_post == None:
                print(f"{self} fails check, as post {fav_post_id} in their favorites fails check.")
                return False

        return True

class Post:
    def __init__(self, sqlite_row=None, raw_atts_dict=None):
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'
        if sqlite_row != None:
            self._init_from_sqlite(sqlite_row)
        if raw_atts_dict != None:
            self._init_from_raw_atts(raw_atts_dict)

    """
        Initialize the class from a row in the sqlite database.
    """
    def _init_from_sqlite(self, sqlite_row):
        self.has_sqlite_atts = True
        self.by = sqlite_row[0]
        self.id = sqlite_row[1]
        self.score = int(sqlite_row[2])
        self.time = int(sqlite_row[3])
        self.title = sqlite_row[4]
        self.text = sqlite_row[5]
        self.url = sqlite_row[6]
        self.url_content = sqlite_row[7]
        self.misc_json = sqlite_row[8]

    """
        Initilaize the class from a raw atts dict.
    """
    def _init_from_raw_atts(self, raw_atts_dict):
        self.by = raw_atts_dict["by"]
        self.id = raw_atts_dict["id"]
        self.score = raw_atts_dict["score"]
        self.time = int(raw_atts_dict["time"])
        self.title = raw_atts_dict["title"]
        self.text = raw_atts_dict["text"]
        self.url = raw_atts_dict["url"]
        self.url_content = raw_atts_dict["url_content"]
        self.misc_json = raw_atts_dict["misc_json"]

    def __str__(self):
        contents = "post:\n"
        contents += f"""
            id: {self.id}
            author: {self.by}
            title: {self.title}
            created: {datetime.datetime.fromtimestamp(self.time)}
        """
        return contents

    """
        Check this post to see whether or not it contains everything necessary
        in creation of a full feature set.

        TODO: this should probably check the user pool as opposed to the database?

    """
    def check(self, sqlite_cursor):
        if self._DEBUG_IGNORE_CHECK: 
            return True
        author = sqlite_utils.get_user_profile(sqlite_cursor, self.by)

        if author == None:
            print(f"{self} fails check, as its author could not be retrieved.")
            return False

        author_passes = author.check()

        if not author_passes:
            print(f"{self} fails check, as its author failed check.")
            return False

        return True

class Comment:
    def __init__(self, sqlite_row=None, raw_atts_dict=None):
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'
        if sqlite_row != None:
            self._init_from_sqlite(sqlite_row)
        if raw_atts_dict != None:
            self._init_from_raw_atts(raw_atts_dict)

    """
        Initialize the class from a row in the sqlite database.
    """
    def _init_from_sqlite(self, sqlite_row):
        self.by = sqlite_row[0]
        self.id = sqlite_row[1]
        self.time = int(sqlite_row[2])
        self.text = sqlite_row[3]
        self.misc_json = sqlite_row[4]

    """
        Initilaize the class from a raw atts dict.
    """
    def _init_from_raw_atts(self, raw_atts_dict):
        self.by = raw_atts_dict["by"]
        self.id = raw_atts_dict["id"]
        self.time = int(raw_atts_dict["time"])
        self.text = raw_atts_dict["text"]
        self.misc_json = raw_atts_dict["misc_json"]

    def __str__(self):
        contents = "comment:\n"
        contents += f"""
            id: {self.id}
            author: {self.by}
            text: {self.text}
            created: {datetime.datetime.fromtimestamp(self.time)}
        """        
        return contents

    """
        Check this comment to see whether or not it contains everything necessary
        in creation of a full feature set.

        TODO: this should probably check the user pool as opposed to the database?
    """
    def check(self, sqlite_cursor):
        if self._DEBUG_IGNORE_CHECK: 
            return True
        author = sqlite_utils.get_user_profile(sqlite_cursor, self.by)

        if author == None:
            print(f"{self} fails check, as its author could not be retrieved.")
            return False

        author_passes = author.check()

        if not author_passes:
            print(f"{self} fails check, as its author failed check.")
            return False

        return True

"""
    A class to represent content strings to be used throughout training and running
    the models, recursively containing children in a questionably efficient manner.
"""
class ContentString:
    def __init__(self, cs_dict, has_sqlite_atts=False, is_root=False):
        self.has_sqlite_atts = has_sqlite_atts
        self.id = cs_dict["id"]
        self.is_root = is_root
        self.active = False

        self.kids = [ContentString(kid_cs_dict, has_sqlite_atts=has_sqlite_atts) for kid_cs_dict in cs_dict["kids"]]

    def __str__(self):
        return json.dumps(self.convert_to_dict(), indent=4)

    def activate(self):
        self.active = True
    
    def deactivate(self):
        self.active = False

    def is_active(self):
        return self.active

    def get_id(self):
        return self.id

    """
        Get a descendant of this content string.
    """
    def get_descendant(self, descendant_id, sqlite_cursor=None):
        return self.dfs(lambda c: c["me"] if c["me"]["self"].id == descendant_id else c["kids"], sqlite_cursor=sqlite_cursor, reduce_kids_f=lambda acc, c: c if c != None else acc,reduce_kids_acc=None)

    """
        Get the parent of a given id in this content string.
    """
    def get_parent_of_descendant(self, child_id,sqlite_cursor=None):
        if self.check_contains_id(child_id):
            return self.dfs(lambda c: c["me"] if (child_id in c["me"]["self"].kids) else c["kids"], sqlite_cursor=sqlite_cursor, reduce_kids_f=lambda acc, c: c if c != None else acc, reduce_kids_acc=None)
        else:
            return None
    
    """
        Remove some descendant of this content string.
    """
    def remove_descendant(self, descendant_id):
        parent = self.get_parent_of_descendant(descendant_id)["self"]
        new_kids = [kid for kid in parent.kids if kid.id != descendant_id]
        parent.kids = new_kids

    """
        Add a comment to some arbitrary parent in this content strings descendants.
    """
    def add_comment_to_descendant(self, child_id, parent_id, has_sqlite_atts=False):
        parent = self.get_descendant(parent_id)["self"]
        kid_cs_dict = {"id": child_id, "kids": []}
        parent.kids.append(ContentString(kid_cs_dict, has_sqlite_atts=has_sqlite_atts))

    """
        Add a comment to this content string.
    """
    def add_direct_comment(self, child_id, has_sqlite_atts=False):
        kid_cs_dict = {"id": child_id, "kids": []}
        self.kids.append(ContentString(kid_cs_dict, has_sqlite_atts=has_sqlite_atts))

    """
        Fetch the full contents of this string,
        returns data from all current data sources, and 
        self to allow modification.

        TODO: fix, this can't be good
    """
    def fetch_contents(self, sqlite_cursor=None):
        if sqlite_cursor == None:
            body = None
        else:
            if self.is_root:
                if self.has_sqlite_atts:
                    body = sqlite_utils.get_post(sqlite_cursor, self.id)
                else: 
                    body = None
            else:
                if self.has_sqlite_atts:
                    body = sqlite_utils.get_comment(sqlite_cursor, self.id)
                else:
                    body = None
        return {
            "body": body,
            "self": self
        }


    """
        Check all items in this content string 
        to see whether all of the data necessary to 
        generate a full feature set with it is present, and 
        if not, remove it, and all of its descendants.
    """
    def clean(self, sqlite_cursor):
        try:
            contents = self.fetch_contents(sqlite_cursor=sqlite_cursor)
            if contents["body"].check(sqlite_cursor):
                clean_kids = [kid for kid in self.kids if kid.clean(sqlite_cursor)]
                self.kids = clean_kids
                return True
            else:
                return False
        except Exception as e:
            print(f"Error in retrieving content string from sqlite: ")
            print(e)
            print("Removing.\n")
            return False

    """
        Convert back to the original dict form.
    """
    def convert_to_dict(self):
        return self.dfs(lambda c: {"id": c["me"]["self"].id, "kids": c["kids"]}, reduce_kids_f=lambda acc, c: [*acc, c], reduce_kids_acc=[])

    """
        Iterate through this content string and its children via a DFS.
        Many options provided.
        TODO: should all parents necessarily be passed into f?
    """
    def dfs(self, f, sqlite_cursor=None ,store_parents=False, parents=[], filter_f=None, reduce_kids_f=None, reduce_kids_acc=None,depth=0):
        contents = self.fetch_contents(sqlite_cursor=sqlite_cursor)

        f_inp = {
            "me": contents,
            "parents": None,
            "kids": None,
            "depth": depth
        }

        if store_parents:
            f_inp["parents"] = parents
            new_parents = [parent for parent in parents]
            new_parents.append(contents)
            parents = new_parents

        if filter_f != None:
            filter_res = filter_f(f_inp)
            if filter_res == False:
                return None

        kid_results = [kid.dfs(f, sqlite_cursor=sqlite_cursor, store_parents=store_parents, parents=parents, filter_f=filter_f, reduce_kids_f=reduce_kids_f,reduce_kids_acc=reduce_kids_acc,depth=depth+1) for kid in self.kids] 

        if reduce_kids_f != None:
            reduced = functools.reduce(reduce_kids_f, kid_results, reduce_kids_acc)
            f_inp["kids"] = reduced

        return f(f_inp)

    """
        Recursively activate all children prior to a given time.
    """
    def activate_before_time(self, sqlite_cursor, time):

        filter_f = lambda c: c["me"]["body"].time < time if c["me"]["body"] != None else False
        activate = lambda c: c["me"]["self"].activate()
        self.dfs(activate, sqlite_cursor=sqlite_cursor, filter_f=filter_f)

    """
        Recursively retrieve a list of all active content strings.
    """
    def get_all_active_content_strings(self, sqlite_cursor):
        
        filter_f = lambda c: c["me"]["self"].is_active()

        reduce_kids_f = lambda acc, c: acc if c == None else [*acc, *c]

        reduce_kids_acc = []

        f = lambda c: [*[[c["me"]["body"]] + kid for kid in c["kids"]], [c["me"]["body"]]]
        
        return self.dfs(f, sqlite_cursor=sqlite_cursor, filter_f=filter_f, reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc)

    """
        Get all descendant ids in a flattened list.
    """
    def get_all_descendants(self):
        return self.dfs(lambda c: [c["me"]["self"].id, *c["kids"]], reduce_kids_f=lambda acc, c: [*acc, *c], reduce_kids_acc=[])

    """
        Check if a given ID is present.
    """
    def check_contains_id(self, given_id):
        return self.get_descendant(given_id) != None

"""
    A class to represent a user pool to be used in training and running the models.
"""
class UserPool:
    def __init__(self, name, sqlite_cursor, username_list=None):
        self.name = name
        self.has_sqlite_atts = False
        if username_list != None:
            self._init_from_username_list(sqlite_cursor, username_list)

    """
        Initialize, given a username list from a JSON in the format
        of a dataset produced in the data module.
    """
    def _init_from_username_list(self, sqlite_cursor, username_list):
        self.has_sqlite_atts = True
        self.users = []
        for username in username_list:
            try:
                user = sqlite_utils.get_user_profile(sqlite_cursor, username)
                self.users.append(user)
            except Exception as e:
                print("Error in retrieving user from sqlite:")
                print(e)
                print("Removing.\n")

    def __str__(self):
        return f"user pool {self.name}"

    def get_users(self):
        return self.users

    """
        Run a given function on all users.
    """
    def run_func_on_users(self, f, filter_f=lambda u: True):
        return [f(user) for user in self.users if filter_f(user)]

    def check_contains_user(self, username):
        return len(self.run_func_on_users(lambda u: u, filter_f=lambda u: u.username == username)) == 1

    def get_user(self, username):
        if self.check_contains_user(username):
            return self.run_func_on_users(lambda u: u, lambda u: u.username == username)[0]
        else:
            return None

    def add_users(self, new_users):
        self.users = [*self.users, *new_users]

    def remove_users(self, usernames_to_remove):
        new_users = [user for user in self.users if not (user.username in usernames_to_remove)]
        self.users = new_users

    def get_username_list(self):
        return [user.username for user in self.users]

    """
        Clean this user pool by checking each user and removing all
        who fail.
    """
    def clean(self, sqlite_cursor):
        clean_users = [user for user in self.users if user.check(sqlite_cursor)]
        self.users = clean_users

    

"""
    A class to represent a dataset, to be used in both training and running the models.
"""
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

        (self.sqlite_cursor, self.sqlite_conn) = sqlite_utils.connect_to_sqlite(self.dataset_path + "data.db")

        usernames = utils.read_json(self.dataset_path + "usernames.json")
        cs_dicts = utils.read_json(self.dataset_path + "contentStringLists.json")

        self.user_pool = UserPool(self.name, self.sqlite_cursor, username_list=usernames)
        self.content_strings = [ContentString(cs_dict, has_sqlite_atts=True, is_root=True) for cs_dict in cs_dicts]        

    def __str__(self):
        return f"""
            dataset {self.name}
        """

    def get_sqlite_cursor(self):
        return sqlite_cursor

    def get_initial_time(self):
        return self.initial_time
    
    def get_current_time(self):
        return self.current_time

    def get_current_cs_dict(self):
        return self.run_func_on_roots(lambda c: c.convert_to_dict())

    def get_current_username_list(self):
        return self.user_pool.get_username_list()

    def check_contains_id(self, member_id):
        print(self.run_func_on_roots(lambda r: r.check_contains_id(member_id)))
        return False
        return len() == 1

    def get_member_item(self, member_id):
        if self.check_contains_id(member_id):
            return self.run_func_on_roots(lambda r: r, filter_f=lambda r: r.check_contains_id(member_id))[0].get_descendant(member_id, sqlite_cursor=self.sqlite_cursor)
        else:
            return None

    """
        Add a set of users to the dataset, given a list of attribute dicts.
    """
    def add_users(self, user_dict_list):
        insert_success = sqlite_utils.insert_user_profiles(self.sqlite_cursor, self.sqlite_conn, self.dataset_path, user_dict_list)
        if insert_success:
            new_users = [UserProfile(raw_atts_dict=user_dict) for user_dict in user_dict_list]
            self.user_pool.add_users(new_users)

    """
        Remove a list of users from the dataset, given their usernames.
    """
    def remove_users(self, username_list):
        try:
            users = [self.user_pool.get_user(username) for username in username_list]
            for user in users:
                sqlite_utils.remove_items(self.sqlite_cursor, self.sqlite_conn, "posts", user.post_ids)
                sqlite_utils.remove_items(self.sqlite_cursor, self.sqlite_conn, "comments", user.comment_ids)

            sqlite_utils.remove_items(self.sqlite_cursor, self.sqlite_conn, "userProfiles", username_list)

            self.user_pool.remove_users(username_list)

            new_username_list = self.user_pool.get_username_list()
            utils.write_json(new_username_list, self.dataset_path + "usernames.json")

            new_cs_dicts = self.get_current_cs_dict()
            utils.write_json(new_cs_dicts, self.dataset_path + "contentStringLists.json")

            print("Successfully removed users:")
            [print(username) for username in username_list]
            print("and all of their submissions from the dataset.")

            return True
        except Exception as e:
            print("Error removing users from the dataset:")
            print(e)
            return False

   
    """
        Remove a root post from the dataset.
    """
    def remove_post(self, post_id):
        try:
            post = self.run_func_on_roots(lambda r: r, filter_f=lambda r: r.id == post_id)
            author_username = post.fetch_contents(sqlite_cursor=sqlite_cursor)["body"].by

            sqlite_utils.remove_items(self.sqlite_cursor, self.sqlite_conn, "posts", post_id)

            sqlite_utils.remove_post_ids_from_user(self.sqlite_cursor, self.sqlite_conn, author_username, [post_id])

            new_content_strings = self.run_func_on_roots(lambda r: r, filter_f=lambda r: r.id == post_id)
            self.content_strings = new_content_strings

            new_cs_dict = self.get_current_cs_dict()
            utils.write_json(new_cs_dict, self.dataset_path + "contentStringLists.json")

            print(f"Successfully removed post with id {post_id} and all of its descendants from the dataset.")
            return True
            
        except Exception as e:
            print("Error removing post from the dataset:")
            print(e)
            return False

    """
        Remove a comment from the dataset, given its id.
    """
    def remove_comment(self, comment_id):
        try:
            comment = self.get_member_item(comment_id)
            print(comment)
            author_username = comment["body"].by

            descendant_ids = comment["self"].get_all_descendants()
            sqlite_utils.remove_items(self.sqlite_cursor, self.sqlite_conn, "comments", descendant_ids)
            self.run_func_on_roots(lambda r: r.remove_descendant(comment_id), filter_f=lambda r: r.check_contains_id(comment_id))[0]

            sqlite_utils.remove_comment_ids_from_user(self.sqlite_cursor, self.sqlite_conn, author_username, [comment_id])

            new_cs_dict = self.get_current_cs_dict()
            utils.write_json(new_cs_dict, self.dataset_path + "contentStringLists.json")

            print(f"Successfully removed comment with id {comment_id} and all of its descendants from the dataset.")
            return True
            
        except Exception as e:
            print("Error removing comment from the dataset:")
            print(e)
            return False

    """
        Add a set of new root posts to the dataset, given a list of attribute dicts
    """
    def add_root_posts(self, post_dict_list):
        insert_success = sqlite_utils.insert_posts(self.sqlite_cursor, self.sqlite_conn, self.dataset_path, post_dict_list)
        if insert_success:
            cs_dicts = [{"id": post_dict["id"], "kids": []} for post_dict in post_dict_list]
            new_roots = [ContentString(cs_dict, has_sqlite_atts=True, is_root=True) for cs_dict in cs_dicts]
            self.content_strings = [*self.content_strings, *new_roots]

    """
        Add a comment to the dataset, given a list of attribute dicts, 
        which must also contain a direct parent id and root id.
    """
    def add_comment(self, comment_dict, parent_id):
        parent = self.get_member_item(parent_id)["self"]
        if parent == None:
            print(f"Error adding comments: the given parent ID is not in the dataset.")

        insert_success = sqlite_utils.insert_comments(self.sqlite_cursor, self.sqlite_conn, [comment_dict])
        parent.add_direct_comment(comment_dict["id"], parent_id)        

        utils.write_json(self.get_current_cs_dict(), self.dataset_path + "contentStringLists.json")
        print(f"Successfully added comment {comment_dict['id']} to the dataset, under parent {parent_id}.")

    """
        Clean all of the content strings in the dataset.
    """
    def clean_content_strings(self):
        clean_content_strings = [root for root in self.content_strings if root.clean(self.sqlite_cursor)]
        self.content_strings = clean_content_strings

    """
        Run a given function on all root content strings.
    """
    def run_func_on_roots(self, f, filter_f=lambda c: True):
        return [f(content_string) for content_string in self.content_strings if filter_f(content_string)]

    """
        Print all content strings.
    """
    def print_content_strings(self):
        self.run_func_on_roots(print)

    """
        Run a given function on all active content strings in the dataset,
        with a DFS traversal at each root.
    """        
    def dfs_all_content_strings(self, f, sqlite_cursor=False ,store_parents=False, parents=[], filter_f=None,reduce_kids_f=None,reduce_kids_acc=None):
        results = [content_string.dfs(f, sqlite_cursor=(self.sqlite_cursor if sqlite_cursor else None), store_parents=store_parents, parents=parents, filter_f=filter_f, reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc) for content_string in self.content_strings]
        return results

    """
        Activate all content strings made prior to a given time.
    """
    def activate_before_time(self, time):
        self.run_func_on_roots(lambda r: r.activate_before_time(self.sqlite_cursor, time))

    """
        Advance the current time by a given amount.
    """
    def advance_current_time(self, amount):
        self.current_time += amount

    """
        Get all active content strings.
        (Full comment chains a user could respond to)
        TODO: come up with better names for this shit
    """
    def get_all_active_content_strings(self):
        root_combs = self.run_func_on_roots(lambda r: r.get_all_active_content_strings(self.sqlite_cursor))
        all_combs = functools.reduce(lambda acc, c: [*acc, *c], root_combs, [])
        return all_combs

    """
        Initialize the dataset for a run.
    """
    def initialize_for_run(self, initial_time=None):
        print(f"Initializing dataset {self.name} for run...")

        print("Cleaning user pool...")
        self.user_pool.clean(self.sqlite_cursor)

        print("Cleaning content strings...")
        self.clean_content_strings()

        #If no initial time is specified,
        #Find the time at which the latest root post was made, and set that at the initial time.
        if initial_time == None:
            print("Finding initial time...")
            root_post_times = [content_string.fetch_contents(sqlite_cursor=self.sqlite_cursor)["body"].time for content_string in self.content_strings]
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
        of active content strings and users
    """
    def get_all_current_feature_sets(self):
        print(f"Getting feature sets for time {self.current_time}")
        
        print(f"Activating all content strings prior to that time...")
        self.activate_before_time(self.current_time)

        users = self.user_pool.get_users()
        print(f"Number of users: {len(users)}")

        all_content_strings = self.get_all_active_content_strings()
        print(f"Number of potential response items: {len(all_content_strings)}")

        feature_sets = []
        for user in users:
            for cs in all_content_strings:
                #TODO: function to create final feature set
                feature_set = f"user: {user}, cs: {cs}"
                feature_sets.append(feature_set)

        print(f"Successfully got all current feature sets for time {self.current_time}.")
        print(f"Number of feature sets: {len(feature_sets)}")
        return feature_sets



