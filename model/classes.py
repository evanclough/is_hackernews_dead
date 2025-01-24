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
    def __init__(self, username, sqlite_atts_dict=None, sqlite_db=None, chroma_db=None):
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'

        self.username = username

        if sqlite_atts_dict != None:
            self._init_from_sqlite_atts(sqlite_atts_dict)
        if sqlite_db != None:
            self._load_from_sqlite(sqlite_db, username)
        if chroma_db != None:
            self._load_from_chroma(chroma_db, username)
        
    """
        Initialize the class from a dict with all of the attributes from the sqlite table.
    """
    def _init_from_sqlite_atts(self, sqlite_atts_dict):
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

    """
        Load in attributes for the given username from sqlite.
    """
    def _load_from_sqlite(self, sqlite_db, username):
        sqlite_row = sqlite_db.get_user_profile_row(username)

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
        Load in attributes for the given username from chroma.
    """
    def _load_from_chroma(self, chroma_db, username):
        print(f"loaded data from chroma for user {username}")

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
            post = Post(post_id, sqlite_db=sqlite_db)
            if post == None:
                print(f"{self} fails check, as post {post_id} in their history fails check.")
                return False
        
        for comment_id in self.comment_ids:
            comment = Comment(comment_id, sqlite_db=sqlite_db)
            if comment == None:
                print(f"{self} fails check, as comment {comment_id} in their history fails check.")
                return False

        for fav_post_id in self.favorite_post_ids:
            fav_post = Post(post_id, sqlite_db=sqlite_db)
            if fav_post == None:
                print(f"{self} fails check, as post {fav_post_id} in their favorites fails check.")
                return False

        return True

    """
        Retrieve this user's history for a given submission type from the database and 
        add it as an attribute.
    """
    def store_submissions_by_type(self, sqlite_db, submission_type, skip_errors=False):
        items = []

        if submission_type == "posts":
            item_ids = self.post_ids
        elif submission_type == "comments":
            item_ids = self.comment_ids
        elif submission_type == "favorites":
            item_ids = self.favorite_post_ids
        else:
            raise UserProfileError("Invalid submission type passed to store_submissions")
        
        get_method = lambda c: Comment(c, sqlite_db=sqlite_db) if submission_type == "comments" else lambda p: Post(p, sqlite_db=sqlite_db)

        for item_id in item_ids:
            try:
                item = get_method(item_id)
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

    """
        Store all of the user's submission items.
    """
    def store_all_submissions(self, sqlite_db, skip_errors=False):
        self.store_submissions_by_type(sqlite_db, "posts", skip_errors=skip_errors)
        self.store_submissions_by_type(sqlite_db, "comments", skip_errors=skip_errors)
        self.store_submissions_by_type(sqlite_db, "favorites", skip_errors=skip_errors)


"""
    For post errors.
"""
class PostError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Post:
    def __init__(self, post_id, sqlite_atts_dict=None, sqlite_db=None, chroma_db=None):
        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'

        self.has_sqlite_atts = False
        self.has_embeddings = False

        print(f"Loading post with id {post_id}...")

        self.id = post_id

        if sqlite_atts_dict != None:
            self._init_from_sqlite_atts(sqlite_atts_dict)
        if sqlite_db != None:
            self._load_from_sqlite(sqlite_db)
        if chroma_db != None:
            self._load_from_chroma(chroma_db)

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
        contents = f"""
        Post {self.id}:
            id: {self.id}
        """
        if self.has_sqlite_atts:
            contents += f"""
            author: {self.by}
            title: {self.title}
            created: {datetime.datetime.fromtimestamp(self.time)}
            text: {self.text}
            url: {self.url}
            misc json: {json.dumps(self.misc_json)}
        """
        else:
            contents += "\nDoes not have sqlite attributes."

        contents += f"\n Embeddings are {'' if self.has_embeddings else ''} loaded."

        return contents

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
        Check this post to see whether or not it contains everything necessary
        in creation of a full feature set.
    """
    def check(self, sqlite_db, chroma_db):
        if self._DEBUG_IGNORE_CHECK: 
            return True

        print(f"Checking if post with id {self.id} contains all necessary attributes for feature creation...")
        if not self.has_sqlite_atts:
            print(f"Post with id {self.id} fails check, as it does not have sqlite attributes.")
            return False
        
        if not self.has_embeddings:
            print(f"Post with id {self.id} fails check, as it does not have embeddings.")

        try:
            author = UserProfile(self.by, sqlite_db=sqlite_db, chroma_db=chroma_db)
            if not author.check(sqlite_db, chroma_db):
                print(f"Post with id {self.id} fails check, as its author fails check.")
                return False
        except Exception as e:
            print(f"Post with id {self.id} fails check, as its author could not be loaded.")
            return False
    
        return True

class Comment:
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
        contents = f"""
        Comment {self.id}:
        """

        if self.has_sqlite_atts:
            contents += f"""
            author: {self.by}
            text: {self.text}
            created: {datetime.datetime.fromtimestamp(self.time)}
            misc json: {json.dumps(self.misc_json)}
            """
        else:
            contents += "\nDoes not have sqlite attributes."
        
        contents += f"Embeddings are {'' if self.has_embeddings else 'not'} loaded. "

        return contents

    """
        Check this comment to see whether or not it contains everything necessary
        in creation of a full feature set.
    """
    def check(self, sqlite_db, chroma_db):
        if self._DEBUG_IGNORE_CHECK: 
            return True

        print(f"Checking if comment with id {self.id} contains all necessary attributes for feature creation...")
        if not self.has_sqlite_atts:
            print(f"Comment with id {self.id} fails check, as it does not have sqlite attributes.")
            return False
        
        if not self.has_embeddings:
            print(f"Comment with id {self.id} fails check, as it does not have embeddings.")

        try:
            author = UserProfile(self.by, sqlite_db=sqlite_db, chroma_db=chroma_db)
            if not author.check(sqlite_db, chroma_db):
                print(f"Comment with id {self.id} fails check, as its author fails check.")
                return False
        except Exception as e:
            print(f"Comment with id {self.id} fails check, as its author could not be loaded.")
            return False
    
        return True

