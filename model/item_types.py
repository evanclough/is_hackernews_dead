"""
    Classes for item types.
"""

import utils

class ItemLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)

class ItemType:

    @classmethod
    def set_base_attributes(cls, base_attributes):
        cls.base_attributes = base_attributes

    @classmethod
    def set_features(cls, features):
        cls.features = features

    def __init__(self, identifier, item_type, atts_dict=None, sqlite_db=None, chroma_db=None, verbose=False):
        self.identifier = identifier

        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'
        self.has_atts = False
        self.has_embeddings = False
        self.verbose = verbose
        
        self.item_type = item_type
        self.atts_info = [att for att in (self.base_attributes + self.features) if att["item_type"] == self.item_type]
        self.atts_dict = {}
        for att in self.atts_info:
            self.atts_dict[att["name"]] = None
        
        self._print(f"Initialzing {self}...")

        if atts_dict != None:
            self._init_from_atts_dict(atts_dict)
        if sqlite_db != None:
            self._load_from_sqlite(sqlite_db)
        if chroma_db != None:
            self._load_from_chroma(chroma_db)

        self._print(f"Successfully initialized {self}.")


    def _init_from_atts_dict(self, atts_dict):
        self._print("Manually populating attributes from given dict for {self}...")
        for att, value in atts_dict.items():
            if att in self.atts_dict:
                self.atts_dict[att] = value
            else:
                raise ItemLoadError(f"Attempted to insert non-existant attribute {att} into {self}")
    
        self._print("Successfully populated attributes from given dict for {self}.")


    def _load_from_sqlite(self, sqlite_db):
        self._print("Loading attributes from sqlite for {self}...")
        sqlite_row = sqlite_db.get_item_row_by_identifier(self.item_type, self.identifier)
        att_list = sorted(self.atts_info, key=lambda l: l["sqlite_order"])

        for i in range(len(att_list)):
            self.atts_dict[att_list[i]["name"]] = sqlite_row[i]
        self.has_atts = True

        self._print("Successfully loaded attributes from sqlite for {self}.")

    def _load_from_chroma(self, chroma_db):
        self._print("Loading embeddings from chroma...")
        embeddings = chroma_db.get_embeddings_for_datatype(item_type, [self.identifier])

        if len(embeddings) != 1:
            raise ItemLoadError(f"Error loading embeddings for {self}: length of retrieved embeddings is {len(embeddings)}")

        self.embeddings = embeddings[0]
        self.has_embeddings = True

        self._print("Successfully loaded embeddings from chroma.")



    def set_verbose(self, verbose):
        self.verbose = verbose
    
    def _print(self, s):
        if self.verbose:
            print(s)



    def __str__(self):
        return f"item with identifier {self.identifier} of type {self.item_type}"

    def _long_str(self):
        contents = str(self) + "\n"
        if self.has_atts:
            for att, value in self.atts_dict.items():
                contents += "\t" + f"{att}: {value}" + "\n"
        else:
            contents += "\tDoes not have attributes loaded.\n"

        contents += "\t" + f"Embeddings are {'' if self.has_embeddings else 'not'} loaded." + "\n"
        
        return contents



    def get_att(self, att):
        if att in self.atts_dict:
            return self.atts_dict[att]
        else:
            raise KeyError(f"Attempted to retrieve non-existant attribute {att} from {self}")
    
    def set_att(self, value):
        if att in self.atts_dict:
            #TODO: check type
            self.atts_dict[att] = value
        else:
            raise KeyError(f"Attempted to set non-existant attribute {att} to value {value} in {self}")

    def get_att_dict(self):
        return self.atts_dict


    def check(self, sqlite_db, chroma_db):
        if self._DEBUG_IGNORE_CHECK: 
            return True
            
        self._print(f"Checking if {self} contains all necessary attributes for feature creation...")

        if not self.has_atts:
            self._print(f"{self} fails check, as it does not have attributes loaded.")
            return False
        
        if not self.has_embeddings:
            self._print(f"{self} fails check, as it does not have embeddings.")
            return False

"""
    For user loading errors.
"""
class UserLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)


class User(ItemType):
    def __init__(self, username, load_submissions=None, skip_submission_errors=False, **kwargs):
        super().__init__(username, "users", **kwargs) 

        self.has_submissions = False

        if load_submissions:
            self._load_submissions(sqlite_db=kwargs["sqlite_db"], chroma_db=kwargs["chroma_db"], skip_errors=skip_submission_errors)
    
    def _long_str(self):
        contents = super()._long_str()

        contents += "\t" + f"Submissions are {'' if self.has_submissions else 'not'} loaded." + "\n"

        return contents

    """
        Store all of the user's submission items.
    """
    def _load_submissions(self, sqlite_db=None, chroma_db=None, skip_errors=False):
        
        self._print(f"Loading submission history for {self}...")

        self.submissions = {
            "posts": {
                "identifier_list": "post_ids",
                "init_func": Post,
                "items": []
            },
            "comments": {
                "identifier_list": "comment_ids",
                "init_func": Comment,
                "items": []
            },
            "favorites": {
                "identifier_list": "favorite_post_ids",
                "init_func": Post,
                "items": []
            }
        }

        for sub_type, sub_dict in self.submissions.items():
            identifier_list = self.get_att(sub_dict["identifier_list"])
            for identifier in identifier_list:
                try:
                    item = sub_dict["init_func"](identifier, sqlite_db=sqlite_db, chroma_db=chroma_db, verbose=self.verbose)
                    sub_dict["items"].append(item)
                except Exception as e:
                    self._print(f"Error in retrieving {sub_type} {identifier} for user {self.identifier}.")
                    if skip_errors:
                        self._print("Skipping...")
                        sub_dict["items"].append(None)
                        continue
                    else:
                        raise e
        
        self.has_submissions = True
        self._print(f"Successfully loaded submission history for {self}.")

    def check(self, sqlite_db, chroma_db):
        super().check(sqlite_db, chroma_db)

        if not self.has_submissions:
            self._print(f"{self} fails check, as they do not have their submissions loaded.")
            return False
        
        for sub_type, sub_dict in self.submissions.items():
            for item in sub_dict["items"]:
                if item == None:
                    self._print(f"{self} fails check, as {sub_type} {sub_dict['identifier']} had an error in retrieval.")
                    return False
                if not item.check(sqlite_db, chroma_db):
                    self._print(f"{self} fails check, as {sub_type} {item} fails check.")
                    return False
        
        self._print(f"{self} passes check.")

        return True

class Submission(ItemType):
    def __init__(self, id, item_type, load_author=False, **kwargs):
        super().__init__(id, item_type, **kwargs)

        self.has_author = False

        if load_author: 
            self._load_author(sqlite_db=kwargs["sqlite_db"], chroma_db=kwargs["chroma_db"])

    def _long_str(self):
        contents = super()._long_str()

        contents += "\t" + f"Author is {'' if self.has_author else 'not'} loaded." + "\n"

        return contents

    def _load_author(self, sqlite_db=None, chroma_db=None):
        self._print(f"Loading author of {self}...")

        if not self.has_atts:
            raise ItemLoadError(f"Error: attempted to load author of {self} that does not have attributes loaded.")
        
        self.author = User(self.get_att("by"), sqlite_db=sqlite_db, chroma_db=chroma_db)
        self.has_author = True

        self._print("Successfully loaded auther of {self}.")

    """
        Check this item to see whether or not it contains everything necessary
        in creation of a full feature set.
    """
    def check(self, sqlite_db, chroma_db):

        super().check(sqlite_db, chroma_db)

        if not self.has_author:
            self._print(f"{self} fails check, as its author is not loaded.")
            return False
        
        if not self.author.check(sqlite_db, chroma_db):
            self._print(f"{self} fails check, as its author fails check.")
            return False

        self._print(f"{self} passes check.")
    
        return True

class Post(Submission):
    def __init__(self, id, **kwargs):
        super().__init__(id, "posts", **kwargs)

class Comment(Submission):
    def __init__(self, id, **kwargs):
        super().__init__(id, "comments", **kwargs)
