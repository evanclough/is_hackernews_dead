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
    def __init__(self, sqlite_row=None):
        self.has_sqlite_atts = False
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'
        if sqlite_row != None:
            self._init_from_sqlite(sqlite_row)

    """
        Initialize the class from a row in the sqlite database.
    """
    def _init_from_sqlite(self, sqlite_row):
        self.has_sqlite_atts = True
        self.username =  sqlite_row[0]
        self.about =  sqlite_row[1]
        self.karma = int(sqlite_row[2])
        self.created = int(sqlite_row[3])
        self.post_ids = json.loads(sqlite_row[4])
        self.comment_ids = json.loads(sqlite_row[5]),
        self.favorite_post_ids = json.loads(sqlite_row[6])
        self.text_samples = json.loads(sqlite_row[7])
        self.interests = json.loads(sqlite_row[8])
        self.beliefs = json.loads(sqlite_row[9])

    def __str__(self):
        contents = "user:\n"
        if self.has_sqlite_atts:
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
    def __init__(self, sqlite_row=None):
        self.has_sqlite_atts = False
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'
        if sqlite_row != None:
            self._init_from_sqlite(sqlite_row)

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
        self.text = sqlite_row[5],
        self.url = sqlite_row[6],
        self.urlContent = sqlite_row[7]

    def __str__(self):
        contents = "post:\n"
        if self.has_sqlite_atts:
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
    def __init__(self, sqlite_row=None):
        self.has_sqlite_atts = False
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'

        if sqlite_row != None:
            self._init_from_sqlite(sqlite_row)

    """
        Initialize the class from a row in the sqlite database.
    """
    def _init_from_sqlite(self, sqlite_row):
        self.has_sqlite_atts = True
        self.by = sqlite_row[0]
        self.id = sqlite_row[1]
        self.time = int(sqlite_row[2])
        self.text = sqlite_row[3]

    def __str__(self):
        contents = "comment:\n"
        if self.has_sqlite_atts:
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
    def __init__(self, sqlite_cs_dict=None, is_root=False):
        self.has_sqlite_atts = False
        
        if sqlite_cs_dict != None:
            self._init_from_raw_cs_dict(sqlite_cs_dict, is_root=is_root)

    """
        Recursively initialize, given a JSON in the format
        of a sqlite dataset produced in the data module.
    """
    def _init_from_raw_cs_dict(self, sqlite_cs_dict, is_root=False):
        self.has_sqlite_atts = True
        self.id = sqlite_cs_dict["id"]
        self.is_root = is_root
        self.active = False

        self.kids = [ContentString(sqlite_cs_dict=kid_cs_dict) for kid_cs_dict in sqlite_cs_dict["kids"]]

    def __str__(self):
        contents = "content string: "
        if self.has_sqlite_atts:
            contents += f"""
                id: {self.id},
                num kids: {len(self.kids)}
            """
        return contents

    def activate(self):
        self.active = True
    
    def deactivate(self):
        self.active = False

    def is_active(self):
        return self.active
    
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
        Iterate through this content string and its children via a DFS.
        Many options provided.
        TODO: should all parents necessarily be passed into f?
    """
    def dfs(self, f, sqlite_cursor=None ,store_parents=False, parents=[], filter_f=None, fold_f=None, fold_acc=None, fold_up=False):
        contents = self.fetch_contents(sqlite_cursor=sqlite_cursor)
        if store_parents:
            f_inp = {
                "me": contents,
                "parents": parents
            }
        else:
            f_inp = contents
        
        if filter_f != None:
            filter_res = filter_f(f_inp)
            if filter_res == False:
                return None

        my_result = f(f_inp)

        new_parents = []
        new_parents = [parent for parent in parents]
        new_parents.append(my_result)

        kid_results = [kid.dfs(f, sqlite_cursor=sqlite_cursor, store_parents=store_parents, parents=new_parents, filter_f=filter_f, fold_f=fold_f,fold_acc=fold_acc) for kid in self.kids] 
        
        if fold_f != None:
            if fold_up: 
                folded = functools.reduce(fold_f, kid_results, fold_acc)
                folded_up = fold_f(folded, my_result)
                return folded_up
            else:
                folded = fold_f(fold_acc, my_result)
                folded_down = functools.reduce(fold_f, kid_results, folded)
                return folded_down
        
    """
        Recursively activate all children prior to a given time.
    """
    def activate_before_time(self, sqlite_cursor, time):
        #check = lambda c: print(f"my time: {c['contents'].time if c['contents'] != None else 'no time'}, given time: {time} active: {c['self'].is_active()}")
        
        #self.dfs(check, sqlite_cursor=sqlite_cursor)

        filter_f = lambda c: c["body"].time < time if c["body"] != None else False
        activate = lambda c: c["self"].activate()
        self.dfs(activate, sqlite_cursor=sqlite_cursor, filter_f=filter_f)
        
        #self.dfs(check, sqlite_cursor=sqlite_cursor)

    """
        Recursively retrieve a list of all active content strings,
        TODO: fix, this is disastrous, but works
    """
    def get_all_active_content_strings(self, sqlite_cursor, is_root=False):
        if is_root:
            self.all_combinations = []
        
        filter_f = lambda c: c["me"]["self"].is_active()
        def f(c):
            if len(c["parents"]) == 0:
                me = [c["me"]["body"]]
                self.all_combinations.append(me)
                return me
            else:
                me = [*c["parents"][-1], c["me"]["body"]]
                self.all_combinations.append(me)
                return me

        self.dfs(f, sqlite_cursor=sqlite_cursor, store_parents=True, filter_f=filter_f)

        return self.all_combinations

"""
    A class to represent a user pool to be used in training and running the models.
"""
class UserPool:
    def __init__(self, name, sqlite_cursor, sqlite_username_list=None):
        self.name = name
        self.has_sqlite_atts = False
        if sqlite_username_list != None:
            self._init_from_sqlite_username_list(sqlite_cursor, sqlite_username_list)

    """
        Initialize, given a username list from a JSON in the format
        of a sqlite dataset produced in the data module.
    """
    def _init_from_sqlite_username_list(self, sqlite_cursor, sqlite_username_list):
        self.has_sqlite_atts = True
        self.users = []
        for username in sqlite_username_list:
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
    def __init__(self, name, sqlite_dataset_name=None):
        self.name = name
        if sqlite_dataset_name != None:
            self._init_from_sqlite(sqlite_dataset_name)
    
    """
        Initialize from a sqlite dataset in the format produced in the data module.
    """
    def _init_from_sqlite(self, sqlite_dataset_name):
        root_dataset_path = utils.fetch_env_var("ROOT_DATASET_PATH")
        dataset_path = root_dataset_path + sqlite_dataset_name + "/"

        self.sqlite_cursor = sqlite_utils.create_sqlite_cursor(dataset_path + "data.db")

        usernames = utils.read_json(dataset_path + "usernames.json")
        cs_dicts = utils.read_json(dataset_path + "contentStringLists.json")

        self.user_pool = UserPool(self.name, self.sqlite_cursor, sqlite_username_list=usernames)
        self.content_strings = [ContentString(sqlite_cs_dict=sqlite_cs_dict, is_root=True) for sqlite_cs_dict in cs_dicts]        

    def __str__(self):
        return f"""
            dataset {self.name}:
            {self.user_pool}
            content strings: {functools.reduce(lambda c, s: c + s, self.content_strings, '')}
        """

    def get_sqlite_cursor(self):
        return sqlite_cursor

    def get_initial_time(self):
        return self.initial_time
    
    def get_current_time(self):
        return self.current_time

    """
        Clean all of the content strings in the dataset.
    """
    def clean_content_strings(self):
        clean_content_strings = [root for root in self.content_strings if root.clean(self.sqlite_cursor)]
        self.content_strings = clean_content_strings

    """
        Run a given function on all root content strings.
    """
    def run_func_on_roots(self, f):
        return [f(content_string) for content_string in self.content_strings]

    """
        Run a given function on all active content strings in the dataset,
        with a DFS traversal at each root.
    """        
    def dfs_all_content_strings(self, f, sqlite_cursor=False ,store_parents=False, parents=[], filter_f=None,fold_f=None,fold_acc=None):
        results = [content_string.dfs(f, sqlite_cursor=(self.sqlite_cursor if sqlite_cursor else None), store_parents=store_parents, parents=parents, filter_f=filter_f, fold_f=fold_f, fold_acc=fold_acc) for content_string in self.content_strings]
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
        root_combs = self.run_func_on_roots(lambda r: r.get_all_active_content_strings(self.sqlite_cursor, is_root=True))
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
        print(f"num users: {len(users)}")

        all_content_strings = self.get_all_active_content_strings()
        print(f"num cs: {len(all_content_strings)}")

        feature_sets = []
        for user in users:
            for cs in all_content_strings:
                #TODO: function to create final feature set
                feature_set = f"user: {user}, cs: {cs}"
                feature_sets.append(feature_set)

        print(f"Successfully got all current feature sets for time {self.current_time}.")
        print(f"num feature sets: {len(feature_sets)}")
        return feature_sets
