"""
    The classes used to represent the three root datatypes, 
    and the classes used for the dataset.
"""

import utils
import sqlite_db

import datetime
import json

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
        contents = f"""
        User Profile of {self.username}:
            about: {self.about}
            created: {self.created}
            user_class: {self.user_class}
        """
        contents += "\ttext samples:\n"
        for text_sample in self.text_samples:
            contents += text_sample + "\n"
        contents += "\n\tinterests:\n"
        for interest in self.interests:
            contents += interest + "\n"
        contents += "\n\tbeliefs:\n"
        for belief in self.beliefs:
            contents += belief + "\n"
        contents += "\n\tmisc json:\n"
        contents += json.dumps(self.misc_json)
        
        return contents


    """
        Check this user profile to see whether or not it contains everything necessary
        in creation of a full feature set.
    """
    def check(self, sqlite_db):
        if self._DEBUG_IGNORE_CHECK: 
            return True
        
        #check each post, comment, and favorite id to make sure its in the database
        for post_id in self.post_ids:
            post = sqlite_db.get_post(post_id)
            if post == None:
                print(f"{self} fails check, as post {post_id} in their history fails check.")
                return False
        
        for comment_id in self.comment_ids:
            comment = sqlite_db.get_comment(comment_id)
            if comment == None:
                print(f"{self} fails check, as comment {comment_id} in their history fails check.")
                return False

        for fav_post_id in self.favorite_post_ids:
            fav_post = sqlite_db.get_post(fav_post_id)
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
        self.by = sqlite_row[0]
        self.id = sqlite_row[1]
        self.score = int(sqlite_row[2])
        self.time = int(sqlite_row[3])
        self.title = sqlite_row[4]
        self.text = sqlite_row[5]
        self.url = sqlite_row[6]
        self.url_content = sqlite_row[7]
        self.misc_json = json.loads(sqlite_row[8])

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
        contents = f"""
        Post {self.id}:
            id: {self.id}
            author: {self.by}
            title: {self.title}
            created: {datetime.datetime.fromtimestamp(self.time)}
            text: {self.text}
            url: {self.url}
            misc json: {json.dumps(self.misc_json)}
        """
        return contents

    """
        Check this post to see whether or not it contains everything necessary
        in creation of a full feature set.

        TODO: this should probably check the user pool as opposed to the database?

    """
    def check(self, sqlite_db):
        if self._DEBUG_IGNORE_CHECK: 
            return True
        author = sqlite_db.get_user_profile(self.by)

        if author == None:
            print(f"{self} fails check, as its author could not be retrieved.")
            return False

        author_passes = author.check(sqlite_db)

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
        self.misc_json = json.loads(sqlite_row[4])

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
        contents = f"""
        Comment {self.id}:
            author: {self.by}
            text: {self.text}
            created: {datetime.datetime.fromtimestamp(self.time)}
            misc json: {json.dumps(self.misc_json)}
        """        
        return contents

    """
        Check this comment to see whether or not it contains everything necessary
        in creation of a full feature set.

        TODO: this should probably check the user pool as opposed to the database?
    """
    def check(self, sqlite_db):
        if self._DEBUG_IGNORE_CHECK: 
            return True
        author = sqlite_db.get_user_profile(self.by)

        if author == None:
            print(f"{self} fails check, as its author could not be retrieved.")
            return False

        author_passes = author.check(sqlite_db)

        if not author_passes:
            print(f"{self} fails check, as its author failed check.")
            return False

        return True

