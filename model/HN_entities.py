import entities


class HNUserLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)

class HNSubmissionLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)

class HNUser(entities.User):
    def __init__(self, *args,  **kwargs):

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

        super().__init__(*args, **kwargs) 


    def _long_str(self):
        contents = super()._long_str()

        contents += "\t" + f"Submissions are {'' if self.has_submissions else 'not'} loaded." + "\n"

        return contents

    def embed_submission_history(self, sub_type, chroma):
        for submission_object in self.atts[sub_type]:
            submission_object.generate_embeddings(chroma)

    """
        Store all of the user's submission items.
    """
    def load_derived_atts(self, sqlite=None, chroma=None, create_post_f=None, create_comment_f=None, skip_submission_errors=False):
        
        self._print(f"Loading submission history for {self}...")

        if create_post_f == None or create_comment_f == None:
            raise HNUserLoadError(f"Error: attempted to load submission history of {self}, but did not provide post or comment creation methods.")

        self.submissions = {
            "posts": {
                "id_list": "post_ids",
                "init_func": create_post_f
            },
            "comments": {
                "id_list": "comment_ids",
                "init_func": create_comment_f
            },
            "favorite_posts": {
                "id_list": "favorite_post_ids",
                "init_func": create_post_f
            }
        }

        for sub_type, sub_dict in self.submissions.items():
            id_list = self.get_att(sub_dict["id_list"])
            self.atts[sub_type] = []
            for id_val in id_list:
                try:
                    submission = sub_dict["init_func"](id_val)
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

    def check_derived_atts(self, submission_checklist=[]):
        
        submission_lists = ["posts", "comments", "favorite_posts"]

        for submission_list in submission_lists:
            if self.atts[submission_list] != None:
                for submission in self.atts[submission_list]:
                    if not (submission.check(checklist=submission_checklist)):
                        return {
                            "success": False,
                            "message": f"{sub_type} {item} in their submission history fails check."
                        }
            else:
                return {
                    "success": False,
                    "message": f"{submission_list} is not present in this user's attributes."
                }

        return {
            "success": True
        }

### author related stuff is stubbed out while testing, the datasets aren't full
class HNSubmission(entities.Submission):
    def __init__(self):

        self.custom_embedding_functions = {
            "author": {
                "load": lambda p: p,
                "store": self.embed_author
            }
        }

    def embed_author(self, chroma):
        return True

    def _long_str(self):
        contents = super()._long_str()

        contents += "\t" + f"Author is {'' if self.has_author else 'not'} loaded." + "\n"

        return contents

    def load_derived_atts(self, sqlite=None, chroma=None, create_user_f=None):
        self._print(f"Loading author of {self}...")

        if create_user_f == None:
            raise HNSubmissionLoadError(f"Error: attempted to load author of {self}, but did not provide create user object method.")

        if not self.has_base_atts:
            raise ItemLoadError(f"Error: attempted to load author of {self} that does not have attributes loaded.")
        
        self.atts['author'] = self.get_att('by')
        #self.atts['author'] = self.create_user_object(self.get_att("by"))
        
        self._print(f"Successfully loaded author of {self}.")

    def check_base_atts(self):
        return {
            "success": True
        }

    def check_embeddings(self):
        return {
            "success": True
        }

    def check_derived_atts(self, author_checklist=[]):


        """
        if not self.atts['author'].check(checklist=author_checklist):
            return {
                "success": False,
                "message": f"Author fails check."
            }
        """
    
        return {
            "success": True
        }

class HNPost(HNSubmission, entities.Root):
    def __init__(self, *args, **kwargs):

        HNSubmission.__init__(self)

        entities.Root.__init__(self, *args, **kwargs)

class HNComment(HNSubmission, entities.Branch):
    def __init__(self, *args, **kwargs):

        HNSubmission.__init__(self)

        entities.Branch.__init__(self, *args, **kwargs)
