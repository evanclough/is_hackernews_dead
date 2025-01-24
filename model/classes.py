"""
    The classes used to represent the three root datatypes, 
    and the classes used for the dataset.
"""

import utils
import sqlite_db

import datetime
import json


"""
    For user profile errors.
"""
class UserProfileError(Exception):
    def __init__(self, message):
        super().__init__(message)

"""
    A class to represent user profiles, to be used
    throughout training and running of the models.
"""
class UserProfile:
    def __init__(self, username, sqlite_atts_dict=None, sqlite_db=None, load_submissions=False, chroma_db=None):
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'

        self.has_sqlite_atts = False
        self.has_submissions = False
        self.has_embeddings = False

        print(f"Loading user profile of {username}...")

        self.username = username

        if sqlite_atts_dict != None:
            self._init_from_sqlite_atts(sqlite_atts_dict)
        if sqlite_db != None:
            self._load_from_sqlite(sqlite_db)
        if load_submissions:
            self._load_submissions(sqlite_db=sqlite_db, chroma_db=chroma_db)
        if chroma_db != None:
            self._load_from_chroma(chroma_db)
        
    """
        Initialize the class from a dict with all of the attributes from the sqlite table.
    """
    def _init_from_sqlite_atts(self, sqlite_atts_dict):
        print(f"Creating user {self.username} from given sqlite attributes...")

        self.username = sqlite_atts_dict["username"]
        self.about = sqlite_atts_dict["about"]
        self.karma = sqlite_atts_dict["karma"]
        self.created = int(sqlite_atts_dict["created"])
        self.user_class = sqlite_atts_dict["user_class"]
        self.post_ids = sqlite_atts_dict["post_ids"]
        self.comment_ids = sqlite_atts_dict["comment_ids"]
        self.favorite_post_ids = sqlite_atts_dict["favorite_post_ids"]
        self.text_samples = sqlite_atts_dict["text_samples"]
        self.interests = sqlite_atts_dict["interests"]
        self.beliefs = sqlite_atts_dict["beliefs"]
        self.misc_json = sqlite_atts_dict["misc_json"]

        self.has_sqlite_atts = True
        print(f"Created user {self.username} from given sqlite attributes.")


    """
        Load in attributes for the given username from sqlite.
    """
    def _load_from_sqlite(self, sqlite_db):
        
        print(f"Loading sqlite attributes for user {self.username}...")
        sqlite_row = sqlite_db.get_user_profile_row(self.username)

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

        self.has_sqlite_atts = True
        print(f"Loaded sqlite attributes for user {self.username}.")

    """
        Retrieve this user's history for a given submission type from the database and 
        add it as an attribute.
    """
    def _load_submissions_by_type(self, submission_type, sqlite_db=None, chroma_db=None, skip_errors=False):
        print(f"Loading {submission_type} for user {self.username}...")

        if not self.has_sqlite_atts:
            raise UserProfileError(f"Error: Attempted to load submissions for user {self.username} that does not have sqlite attributes.")

        items = []

        if submission_type == "posts":
            item_ids = self.post_ids
        elif submission_type == "comments":
            item_ids = self.comment_ids
        elif submission_type == "favorites":
            item_ids = self.favorite_post_ids
        else:
            raise UserProfileError(f"Error: Attempted to load invalid submission type for user {self.username}")
        
        get_method = lambda c: Comment(c, sqlite_db=sqlite_db, chroma_db=chroma_db) if submission_type == "comments" else lambda p: Post(p, sqlite_db=sqlite_db, chroma_db=chroma_db)

        for item_id in item_ids:
            try:
                if submission_type == "comments":
                    item = Comment(item_id, sqlite_db=sqlite_db, chroma_db=chroma_db)
                else:
                    item = Post(item_id, sqlite_db=sqlite_db, chroma_db=chroma_db)
                    
                items.append(item)
            except Exception as e:
                print(f"Error in retriving submission with id {item_id} for user {self.username}'s profile.")
                if skip_errors:
                    print("Skipping...")
                    continue
                else:
                    print(e)
                    raise e
        
        if submission_type == "posts":
            self.posts = items
        elif submission_type == "comments":
            self.comments = items
        else:
            self.favorite_posts = items

        print(f"Loaded {submission_type} for user {self.username}.")

    """
        Store all of the user's submission items.
    """
    def _load_submissions(self, sqlite_db=None, chroma_db=None, skip_errors=False):
        self._load_submissions_by_type("posts", sqlite_db=sqlite_db, chroma_db=chroma_db, skip_errors=skip_errors)
        self._load_submissions_by_type("comments", sqlite_db=sqlite_db, chroma_db=chroma_db, skip_errors=skip_errors)
        self._load_submissions_by_type("favorites", sqlite_db=sqlite_db, chroma_db=chroma_db, skip_errors=skip_errors)

        self.has_submissions = True

    """
        Load in attributes for the given username from chroma.
    """
    def _load_from_chroma(self, chroma_db):
        print(f"Loading embeddings for user {self.username}...")

        embeddings = chroma_db.get_user_profile_embeddings(self.username)

        self.about_embeddings = embeddings["about"]
        self.text_sample_embeddings = embeddings["text_samples"]
        self.beliefs_embeddings = embeddings["beliefs"]
        self.interests_embeddings = embeddings["interests"]

        self.has_embeddings = True
        print(f"Loaded embeddings for user {self.username}.")

    def __str__(self):
        contents = f"User Profile of {self.username}:" + "\n"
        if self.has_sqlite_atts:
            contents += "\t" + f"about: {self.about}" + "\n"
            contents += "\t" + f"created: {datetime.datetime.fromtimestamp(self.created)}" + "\n"
            contents += "\t" + f"user class: {self.user_class}"
            
            contents += "\ttext samples:\n"
            for text_sample in self.text_samples:
                contents +=  "\t\t" + text_sample + "\n"

            contents += "\n\tinterests:\n"
            for interest in self.interests:
                contents += "\t\t" + interest + "\n"

            contents += "\n\tbeliefs:\n"
            for belief in self.beliefs:
                contents += "\t\t" + belief + "\n"

            contents += "\t" + f"misc json: {json.dumps(self.misc_json)}" + "\n"
        else:
            contents += "\tDoes not have sqlite attributes.\n"
        
        contents += "\t" + f"Submissions are {'' if self.has_submissions else 'not'} loaded." + "\n"

        contents += "\t" + f"Embeddings are {'' if self.has_embeddings else 'not'} loaded." + "\n"
        
        return contents

    """
        Get a dictionary containing sqlite attributes for this user
    """ 
    def get_sqlite_att_dict(self):
        if not self.has_sqlite_atts:
            raise UserProfileError(f"Error: attemped to get non existant sqlite attributes for user {self.username}")
        
        return {
            "username": self.username,
            "about": self.about,
            "karma": self.karma,
            "created": self.created,
            "user_class": self.user_class,
            "post_ids": self.post_ids,
            "comment_ids": self.comment_ids,
            "favorite_post_ids": self.favorite_post_ids,
            "text_samples": self.text_samples,
            "interests": self.interests,
            "beliefs": self.beliefs,
            "misc_json": self.misc_json
        }

    """
        Check this user profile to see whether or not it contains everything necessary
        in creation of a full feature set.
    """
    def check(self, sqlite_db, chroma_db):
        if self._DEBUG_IGNORE_CHECK: 
            return True
        
        print(f"Checking if user {self.username} contains all necessary attributes for feature creation...")

        if not self.has_sqlite_atts:
            print(f"User {self.username} fails check, as they do not have sqlite attributes.")
            return False
        
        if not self.has_embeddings:
            print(f"User {self.username} fails check, as they do not have embeddings.")
            return False

        if not self.has_submissions:
            print(f"User {self.username} fails check, as they do not have their submissions loaded.")
            return False
        
        for post in self.posts:
            if not post.check(sqlite_db, chroma_db):
                print(f"User {self.username} fails check, as post with id {post.id} in their history fails check.")
                return False
        
        for comment in self.comments:
            if not comment.check(sqlite_db, chroma_db):
                print(f"User {self.username} fails check, as comment with id {comment.id} in their history fails check.")
                return False
        
        for favorite_post in self.favorite_posts:
            if not favorite_post.check(sqlite_db, chroma_db):
                print(f"User {self.uesrname} fails check, as post with id {post.id} in their favorites fails check.")
                return False
        
        print(f"User {self.username} passes check.")

        return True

"""
    For item errors.
"""
class ItemError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Item:
    def __init__(self, item_id, sqlite_atts_dict=None, sqlite_db=None, load_author=False, chroma_db=None):
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'

        self.has_sqlite_atts = False
        self.has_embeddings = False
        self.has_author = False

        print(f"Loading item with id {item_id}...")

        self.id = item_id

        if sqlite_atts_dict != None:
            self._init_from_sqlite_atts(sqlite_atts_dict)
        if sqlite_db != None:
            self._load_from_sqlite(sqlite_db)
        if load_author: 
            self._load_author(sqlite_db=sqlite_db, chroma_db=chroma_db)
        if chroma_db != None:
            self._load_from_chroma(chroma_db)

    """
        Load in the author of this item.
    """
    def _load_author(self, sqlite_db=None, chroma_db=None):
        if not self.has_sqlite_atts:
            raise ItemError(f"Error: attempted to load author of item with id {self.id} that does not have sqlite attributes.")
        
        self.author = UserProfile(self.by, sqlite_db=sqlite_db, chroma_db=chroma_db)

        self.has_author = True

    """
        Check this item to see whether or not it contains everything necessary
        in creation of a full feature set.
    """
    def check(self, sqlite_db, chroma_db):
        if self._DEBUG_IGNORE_CHECK: 
            return True

        print(f"Checking if item with id {self.id} contains all necessary attributes for feature creation...")

        if not self.has_sqlite_atts:
            print(f"Item with id {self.id} fails check, as it does not have sqlite attributes.")
            return False
        
        if not self.has_embeddings:
            print(f"Item with id {self.id} fails check, as it does not have embeddings.")
            return False

        if not self.has_author:
            print(f"Item with id {self.id} fails check, as its author is not loaded.")
        
        if not self.author.check(sqlite_db, chroma_db):
            print(f"Item with id {self.id} fails check, as its author fails check.")

        print(f"Item with id {self.id} passes check.")
    
        return True

"""
    For post errors.
"""
class PostError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Post(Item):
    """
        Initilaize the class from a dict with all of the sqlite attributes
    """
    def _init_from_sqlite_atts(self, sqlite_atts_dict):
        print(f"Creating post with id {self.id} from given sqlite attributes...")

        self.by = sqlite_atts_dict["by"]
        self.id = sqlite_atts_dict["id"]
        self.score = sqlite_atts_dict["score"]
        self.time = int(sqlite_atts_dict["time"])
        self.title = sqlite_atts_dict["title"]
        self.text = sqlite_atts_dict["text"]
        self.url = sqlite_atts_dict["url"]
        self.url_content = sqlite_atts_dict["url_content"]
        self.misc_json = sqlite_atts_dict["misc_json"]

        self.has_sqlite_atts = True
        print(f"Created post with id {self.id} from given sqlite attributes.")

    """
        Load in attributes from sqlite.
    """
    def _load_from_sqlite(self, sqlite_db):

        print(f"Loading sqlite attributes for post with id {self.id}...")

        sqlite_row = sqlite_db.get_post_row(self.id)

        self.by = sqlite_row[0]
        self.id = sqlite_row[1]
        self.score = int(sqlite_row[2])
        self.time = int(sqlite_row[3])
        self.title = sqlite_row[4]
        self.text = sqlite_row[5]
        self.url = sqlite_row[6]
        self.url_content = sqlite_row[7]
        self.misc_json = json.loads(sqlite_row[8])

        self.has_sqlite_atts = True
        print(f"Loaded sqlite attributes for post with id {self.id}.")

    """
        Load in attributes from chroma.
    """
    def _load_from_chroma(self, chroma_db):
        print(f"Loading embeddings for post with id {self.id}...")

        embeddings = chroma_db.get_post_embeddings(self.id)

        self.title_embeddings = embeddings["title"]
        self.text_content_embeddings = embeddings["text_content"]
        self.url_content_embeddings = embeddings["url_content"]

        self.has_embeddings = True
        print(f"Loaded embeddings for post with id {self.id}.")

    def __str__(self):
        contents = f"Post {self.id}" + "\n"

        if self.has_sqlite_atts:
            contents += "\t" + f"author: {self.by}" + "\n"
            contents += "\t" + f"created: {datetime.datetime.fromtimestamp(self.time)}" + "\n"
            contents += "\t" + f"score: {self.score}" + "\n"
            contents += "\t" + f"text: {self.text}" + "\n"
            contents += "\t" + f"url: {self.url}" + "\n"
            contents += "\t" + f"url_content: {self.url_content}" + "\n"
            contents += "\t" + f"misc json: {json.dumps(self.misc_json)}" + "\n"
        else:
            contents += "\tDoes not have sqlite attributes.\n"
        
        contents += "\t" + f"Author is {'' if self.has_author else 'not'} loaded." + "\n"
        contents += "\t" + f"Embeddings are {'' if self.has_embeddings else 'not'} loaded." + "\n"

        return contents

    """
        Get a dictionary containing sqlite attributes for this post.
    """ 
    def get_sqlite_att_dict(self):
        if not self.has_sqlite_atts:
            raise PostError(f"Error: attemped to get non existant sqlite attributes for post with id {self.id}")
        
        return {
            "by": self.by,
            "id": self.id,
            "time": self.time,
            "text": self.text,
            "title": self.title,
            "url": self.url,
            "url_content": self.url_content,
            "score": self.score,
            "misc_json": self.misc_json
        }

    """
        Create a string concisely describing this post,
        to be passed into the LLM during feature extraction.
    """
    def get_featurex_str(self):
        contents = ""

        if self.has_sqlite_atts:
            contents += f"Title: {self.title}\n"
            if self.text != "":
                contents += f"Text body: {self.text}\n"
            if self.url != "":
                contents += f"Links to: {self.url}\n"
        else:
            raise PostError(f"Error: attempted to generate feature extraction string for post with id {self.id} that does not contain sqlite attributes.")
        
        return contents

"""
    For comment errors.
"""
class CommentError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Comment(Item):
    def __init__(self, comment_id, sqlite_atts_dict=None, sqlite_db=None, chroma_db=None):
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'

        self.has_sqlite_atts = False
        self.has_embeddings = False

        print(f"Loading comment with id {comment_id}...")

        self.id = comment_id

        if sqlite_atts_dict != None:
            self._init_from_sqlite_atts(sqlite_atts_dict)
        if sqlite_db != None:
            self._load_from_sqlite(sqlite_db)
        if chroma_db != None:
            self._load_from_chroma(chroma_db)

    """
        Initilaize the class from a dict containing all of the attributes from the sqlite table.
    """
    def _init_from_sqlite_atts(self, sqlite_atts_dict):
        print(f"Initializing comment with id {self.id} from a dict of sqlite attributes...")

        self.by = sqlite_atts_dict["by"]
        self.id = sqlite_atts_dict["id"]
        self.time = int(sqlite_atts_dict["time"])
        self.text = sqlite_atts_dict["text"]
        self.misc_json = sqlite_atts_dict["misc_json"]

        self.has_sqlite_atts = True
        print(f"Initialized comment with id {self.id} from a dict of sqlite attributes.")


    """
        Load in attributes from sqlite.
    """
    def _load_from_sqlite(self, sqlite_db):
        print(f"Loading sqlite attributes for comment with id {self.id}...")

        sqlite_row = sqlite_db.get_comment_row(self.id)

        self.by = sqlite_row[0]
        self.id = sqlite_row[1]
        self.time = int(sqlite_row[2])
        self.text = sqlite_row[3]
        self.misc_json = json.loads(sqlite_row[4])

        self.has_sqlite_atts = True
        print(f"Loaded sqlite attributes for comment with id {self.id}.")


    """
        Load in attributes from chroma.
    """
    def _load_from_chroma(self, chroma_db):
        print(f"Loading embeddings for comment with id {self.id}...")

        embeddings = chroma_db.get_comment_embeddings(self.id)

        self.text_content_embeddings = embeddings["text_content"]

        self.has_embeddings = True
        print(f"Loaded embeddings for comment with id {self.id}.")

    def __str__(self):
        contents = f"Comment {self.id}" + "\n"

        if self.has_sqlite_atts:
            contents += "\t" + f"author: {self.by}" + "\n"
            contents += "\t" + f"text: {self.text}" + "\n"
            contents += "\t" + f"created: {datetime.datetime.fromtimestamp(self.time)}" + "\n"
            contents += "\t" + f"misc json: {json.dumps(self.misc_json)}" + "\n"
        else:
            contents += "\tDoes not have sqlite attributes.\n"
        
        contents += "\t" + f"Author is {'' if self.has_author else 'not'} loaded." + "\n"
        contents += "\t" + f"Embeddings are {'' if self.has_embeddings else 'not'} loaded." + "\n"

        return contents

    """
        Get a dictionary containing sqlite attributes for this comment.
    """ 
    def get_sqlite_att_dict(self):
        if not self.has_sqlite_atts:
            raise PostError(f"Error: attemped to get non existant sqlite attributes for comment with id {self.id}")
        
        return {
            "by": self.by,
            "id": self.id,
            "time": self.time,
            "text": self.text,
            "misc_json": self.misc_json
        }

