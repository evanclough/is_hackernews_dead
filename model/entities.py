"""
    Classes for entities.
"""

import utils

class ItemLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Entity:

    def __init__(self, id_val, base_atts_dict=None, sqlite_db=None, chroma_db=None, load_derived_atts=False, verbose=False):
        self.id = id_val

        self._DEBUG_IGNORE_CHECK = utils.fetch_env_var("DEBUG_IGNORE_CHECK") != '0'
        self.has_base_atts = False
        self.has_embeddings = False
        self.has_derived_atts = False
        
        self.verbose = verbose

        self.atts = {}
        self.embeddings = {}

        for att_list in self.info_dict['attributes'].values():
            for att in att_list:
                if att['embed']:
                    self.embeddings[att['name']] = None 
                self.atts[att["name"]] = None
        
        self._print(f"Initialzing {self}...")

        if base_atts_dict != None:
            self._init_from_base_atts_dict(base_atts_dict)
        if sqlite_db != None:
            self._load_from_sqlite(sqlite_db)
        if load_derived_atts:
            self.load_derived_atts(sqlite_db=sqlite_db, chroma_db=chroma_db)
            self.has_loaded_atts = True
        if chroma_db != None:
            self._load_from_chroma(chroma_db)

        self._print(f"Successfully initialized {self}.")


    def _init_from_base_atts_dict(self, base_atts_dict):
        self._print(f"Manually populating base attributes from given dict for {self}...")
        for att, value in base_atts_dict.items():
            if att in self.atts:
                self.atts[att] = value
            else:
                raise ItemLoadError(f"Attempted to insert non-existant attribute {att} into {self}")
    
        self.has_base_atts = True

        self._print(f"Successfully populated base attributes from given dict for {self}.")


    def _load_from_sqlite(self, sqlite_db):
        self._print(f"Loading attributes from sqlite for {self}...")
        sqlite_result = sqlite_db.get_by_id(self.entity_type, self.id)

        for att, val in sqlite_result:
            self.atts[att] = val
        
        self.has_base_atts = True

        self._print(f"Successfully loaded attributes from sqlite for {self}.")

    def _load_derived_atts_wrapper(self, sqlite_db=None, chroma_db=None):
        self._print(f"Loading derived attributes for {self}...")

        self.load_derived_atts(sqlite_db=sqlite_db, chroma_db=chroma_db)

        self.has_derived_atts = True

        self._print(f"Successfully loaded derived attributes for {self}.")

    def _load_from_chroma(self, chroma_db):
        self._print(f"Loading embeddings from chroma for {self}...")

        for att_dict_list in self.info_dict['attributes'].values():
            for att_dict in att_dict_list:
                if att_dict['embed']:
                    if att_dict['name'] in self.custom_embedding_functions:
                        self.custom_embedding_functions[att_dict['name']]['load'](chroma_db)
                    else:
                        embeddings = chroma_db.get_embeddings_by_id_list(self.entity_type, att_dict, [self.id])
                        if len(embeddings) != 1:
                            raise ItemLoadError("TODO")
                        else:
                            self.embeddings[att_dict['name']] = embeddings[0]

        self.has_embeddings = True

        self._print(f"Successfully loaded embeddings from chroma for {self}.")

    def store_embeddings(self, chroma_db):
        self._print(f"Generating embeddings and storing in chroma for {self}...")
        for att_dict_list in self.info_dict['attributes'].values():
            for att_dict in att_dict_list:
                if att_dict['embed']:
                    if att_dict['name'] in self.custom_embedding_storers:
                        self.custom_embedding_storers[att_dict['name']]['store'](chroma_db)
                    else:
                        chroma_db.store_embeddings_for_id_list(self.entity_type, att_dict, [self.id], [self.atts[att_dict['name']]])


    def set_verbose(self, verbose):
        self.verbose = verbose
    
    def _print(self, s):
        if self.verbose:
            print(s)



    def __str__(self):
        return f"{self.entity_type} with id {self.id}"

    def _long_str(self):
        contents = str(self) + "\n"
        if self.has_base_atts:
            contents += "\t" + "Base attributes: " + "\n"
            for att, value in self.atts.items():
                if att in s:
                    contents += "\t" + f"{att}: {value}" + "\n"
        else:
            contents += "\tDoes not have base attributes loaded.\n"

        if self.has_loaded_atts:
            contents += "\t" + "Loaded attributes" + "\n"
            for att, value in self.atts.items():
                contents += "\t" + f"{att}: {value}" + "\n"
        else:
            contents += "\tDoes not have loaded attributes.\n"

        contents += "\t" + f"Embeddings are {'' if self.has_embeddings else 'not'} loaded." + "\n"
        
        return contents

    def get_id(self):
        return self.id

    def get_att(self, att):
        if att in self.atts:
            return self.atts[att]
        else:
            raise KeyError(f"Attempted to retrieve non-existant attribute {att} from {self}")
    
    def set_att(self, att, value):
        if att in self.atts:
            #TODO: check type
            self.atts_dict[att] = value
        else:
            raise KeyError(f"Attempted to set non-existant attribute {att} to value {value} in {self}")

    def get_att_dict(self):
        return self.atts


    def check(self, check_base_atts=False, check_embeddings=False, check_derived_atts=False):
        if self._DEBUG_IGNORE_CHECK: 
            return True
            
        att_type_list = [
            {
                "name": "base attributes",
                "check_or_not": check_base_atts,
                "has_or_not": self.has_base_atts,
                "check_f": self.check_base_atts
            },
            {
                "name": "embeddings",
                "check_or_not": check_embeddings,
                "has_or_not": self.has_embeddings,
                "check_f": self.check_embeddings
            },
            {
                "name": "derived",
                "check_or_not": check_derived_atts,
                "has_or_not": self.has_derived_atts,
                "check_f": self.check_derived_atts
            }
        ]

        sources_str = ", ".join([att_type["name"] for att_type in att_type_list if att_type["check_or_not"]])
        self._print(f"Checking {sources_str} of {self}...")

        for att_type in att_type_list:
            if not att_type["has_or_not"]:
                self._print(f"{self} fails check, as it does not have {att_type['name']} loaded.")
                return False
            check_result = att_type['check_f']()
            if not check_result['success']:
                self._print(f"{self} fails check, as its {att_type['name']} failed check: {check_result['message']}.")
                return False
        
        self._print(f"{self} passes check of {sources_str}")
        return True


"""
    For user loading errors.
"""
class UserLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)


class HNUser(Entity):
    def __init__(self, uid, , skip_submission_errors=False, **kwargs):
        self.skip_submission_errors = skip_submission_errors
        self.entity_type = "user"

        self.custom_embedding_functions = {
            "posts": {
                "load": lambda p: p,
                "store": lambda c: self.embed_submission_history("posts", c)
            },
            "comments": {
                "load": lambda p: p,
                "store": lambda c: self.embed_submission_history("comments", c)
            },
            "favorite_posts": {
                "load": lambda p: p,
                "store": lambda c: self.embed_submission_history("favorite_posts", c)
            }
        }

        super().__init__(uid, **kwargs) 


    def _long_str(self):
        contents = super()._long_str()

        contents += "\t" + f"Submissions are {'' if self.has_submissions else 'not'} loaded." + "\n"

        return contents

    def embed_submission_history(self, sub_type, chroma_db):
        for submission_object in self.atts[sub_type]:
            submission_object.store_embeddings(chroma_db)

    """
        Store all of the user's submission items.
    """
    def load_derived_atts(self, sqlite_db=None, chroma_db=None):
        
        self._print(f"Loading submission history for {self}...")

        self.submissions = {
            "posts": {
                "id_list": "post_ids",
                "init_func": root_cls
            },
            "comments": {
                "id_list": "comment_ids",
                "init_func": branch_cls
            },
            "favorites": {
                "id_list": "favorite_post_ids",
                "init_func": root_cls
            }
        }

        for sub_type, sub_dict in self.submissions.items():
            id_list = self.get_att(sub_dict["id_list"])
            self.atts[sub_type] = []
            for id_val in id_list:
                try:
                    submission = sub_dict["init_func"](id_val, sqlite_db=sqlite_db, chroma_db=chroma_db)
                    self.atts[sub_type].append(submission)
                except Exception as e:
                    self._print(f"Error in retrieving {sub_type} {id_val} in submission history of {self}.")
                    if self.skip_submission_errors:
                        self._print("Skipping...")
                        continue
                    else:
                        raise e

        self._print(f"Successfully loaded submission history for {self}.")

    
    def check_base_atts(self):
        return {
            "success": True
        }

    def check_embeddings(self):
        return {
            "success": True
        }

    def check_derived_atts(self):
        
        submission_lists = ["posts", "comments", "favorite_posts"]

        for submission_list in submission_lists:
            for submission in self.atts[submission_list]:
                if not (submission.check()):
                    return {
                        "success": False,
                        "message": f"{sub_type} {item} in their submission history fails check."
                    }

        return {
            "success": True
        }

    def get_embedded_cols(self):
        embedded_att_dict = {}
        for att_list in self.info_dict['attributes'].values():
            for att in att_list:
                if att['embed']:
                    embedded_att_dict[att['name']] = self.atts[att['name']]
        return embedded_att_dict

class HNSubmission(Entity):
    def __init__(self, sub_id, load_author_sub_history=False, **kwargs):
        self.load_author_sub_history = load_author_sub_history

        self.custom_embedding_functions = {
            "author": {
                "load": lambda p: p,
                "store": self.embed_author
            }
        }

        super().__init__(sub_id, **kwargs)

    def embed_author(self, chroma_db):
        self.atts['author'].store_embeddings(chroma_db)

    def _long_str(self):
        contents = super()._long_str()

        contents += "\t" + f"Author is {'' if self.has_author else 'not'} loaded." + "\n"

        return contents

    def load_derived_atts(self, sqlite_db=None, chroma_db=None):
        self._print(f"Loading author of {self}...")

        if not self.has_base_atts:
            raise ItemLoadError(f"Error: attempted to load author of {self} that does not have attributes loaded.")
        
        self.atts['author'] = HNUser(self.get_att("by"), sqlite_db=sqlite_db, chroma_db=chroma_db, load_derived_atts=self.load_author_sub_history)
        
        self._print(f"Successfully loaded author of {self}.")

    def check_base_atts(self):
        return {
            "success": True
        }

    def check_embeddings(self):
        return {
            "success": True
        }

    def check_derived_atts(self):

        if not self.atts['author'].check():
            return {
                "success": False,
                "message": f"Author fails check."
            }
    
        return {
            "success": True
        }

class HNPost(HNSubmission):
    def __init__(self, post_id, **kwargs):
        self.entity_type = "root"

        super().__init__(post_id, **kwargs)

class HNComment(HNSubmission):
    def __init__(self, comment_id, **kwargs):
        self.entity_type = "branch"

        super().__init__(comment_id, **kwargs)
