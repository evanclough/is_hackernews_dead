import entities


class HNUserLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)

class HNUserStoreError(Exception):
    def __init__(self, message):
        super().__init__(message)



class HNSubmissionLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)

class HNSubmissionStoreError(Exception):
    def __init__(self, message):
        super().__init__(message)

class HNUserLoader(entities.DerivedLoader):
    def __init__(self, post_factory, comment_factory, skip_submission_errors=False, **kwargs):
        super().__init__(**kwargs)

        self.params['post_factory'] = post_factory
        self.params['comment_factory'] = comment_factory
        self.params['skip_submission_errors'] = skip_submission_errors

class HNUser(entities.User):

    def embed_submission_history(self, sub_type, chroma):
        for submission_object in self.atts[sub_type]:
            submission_object.pupdate_in_chroma(chroma)

    def delete_sub_his_embeddings(self, sub_type, chroma):
        for submission_object in self.atts[sub_type]:
            submission_object.delete_from_chroma(chroma)

    """
        Store all of the user's submission items.
    """
    def load_derived_atts(self, sqlite, post_factory=None, comment_factory=None, skip_submission_errors=False):
        
        self._print(f"Loading submission history for {self}...")

        if post_factory == None or comment_factory == None:
            raise HNUserLoadError(f"Error: attempted to load submission history of {self}, but did not provide post or comment creation methods.")

        self.submissions = {
            "posts": {
                "id_list": "post_ids",
                "init_func": post_factory
            },
            "comments": {
                "id_list": "comment_ids",
                "init_func": comment_factory
            },
            "favorite_posts": {
                "id_list": "favorite_post_ids",
                "init_func": post_factory
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
                    if skip_submission_errors:
                        self._print("Skipping...")
                        continue
                    else:
                        raise e

        self._print(f"Successfully loaded submission history for {self}.")

    
    def check_base_atts(self):
        return {
            "success": True
        }
    
    def check_generated_atts(self):
        return {
            "success": True
        }

    def check_embeddings(self):
        return {
            "success": True
        }

    def check_derived_atts(self, submission_check_dict):
        
        if not self.status['base']['values']:
            return {
                "success": False,
                "message": f"This user does not have base attributes loaded."
            }

        submission_lists = ["posts", "comments", "favorite_posts"]

        for submission_list in submission_lists:
            if self.atts[submission_list] != None:
                for submission in self.atts[submission_list]:
                    if not (submission.check(check_dict=submission_check_dict)):
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

    custom_embedding_functions = {
        "posts": {
            "load": lambda s, c: 0,
            "pupdate": lambda s, c: HNUser.embed_submission_history(s, "posts", c),
            "delete": lambda s, c: HNUser.delete_sub_his_embeddings(s, "posts", c)
        },
        "comments": {
            "load": lambda s, c: 0,
            "pupdate": lambda s, c: HNUser.embed_submission_history(s, "comments", c),
            "delete": lambda s, c: HNUser.delete_sub_his_embeddings(s, "comments", c)
        },
        "favorite_posts": {
            "load": lambda s, c: 0,
            "pupdate": lambda s, c: HNUser.embed_submission_history(s, "favorite_posts", c),
            "delete": lambda s, c: HNUser.delete_sub_his_embeddings(s, "favorite_posts", c)
        }
    }

class HNSubmissionLoader(entities.DerivedLoader):
    def __init__(self, user_factory, load_author_submission_history=False, **kwargs):
        super().__init__(**kwargs)

        self.params['user_factory'] = user_factory
        self.params['load_author_submission_history'] = load_author_submission_history

### author related stuff is stubbed out while testing, the datasets aren't full
class HNSubmission(entities.Submission):


    def embed_author(self, chroma):
        self.atts['author'].pupdate_in_chroma(chroma)

    def delete_author_embeddings(self, chroma):
        return True

    def load_derived_atts(self, sqlite, user_factory=None, load_author_submission_history=False):
        self._print(f"Loading author of {self}...")

        if user_factory == None:
            raise HNSubmissionLoadError(f"Error: attempted to load author of {self}, but did not provide create user object method.")
        
        self.atts['author'] = user_factory(self.get_att("by"))
        
        self._print(f"Successfully loaded author of {self}.")

    def check_base_atts(self):
        return {
            "success": True
        }

    def check_generated_atts(self):
        return {
            "success": True
        }

    def check_embeddings(self):
        return {
            "success": True
        }

    def check_derived_atts(self, author_check_dict=None):


        if not self.status['base']['values']:
            return {
                "success": False,
                "message": f"This user does not have base attributes loaded."
            }

        """
        if not self.atts['author'].check(check_dict=author_check_dict):
            return {
                "success": False,
                "message": f"Author fails check."
            }
        """
    
        return {
            "success": True
        }

    custom_embedding_functions = {
        "author": {
            "load": lambda s, c: 0,
            "pupdate": lambda s, c: HNSubmission.embed_author(s, c),
            "delete": lambda s, c: HNSubmission.delete_author_embeddings(s, c)
        }
    }

    def pupdate_in_sqlite(self, sqlite, sub_type):
        super().pupdate_in_sqlite(sqlite)

        if self.atts['author'] == None:
            raise HNSubmissionStoreError(f"Error: attempted to update {self} in sqlite, but author is not loaded.")

        id_col = "post_ids" if sub_type == "post" else "comment_ids"
        author_ids = self.atts['author'].get_att(id_col)
        if not (self.id in author_ids):
            self.atts['author'].set_att(id_col, [*author_ids, self.id])
            self.atts['author'].pupdate_in_sqlite(sqlite)

    def delete_from_sqlite(self, sqlite, sub_type):
        super().delete_from_sqlite(sqlite)
        
        if self.atts['author'] == None:
            raise HNSubmissionStoreError(f"Error: attempted to remove {self} from sqlite, but author is not loaded.")

        id_col = "post_ids" if sub_type == "post" else "comment_ids"
        author_ids = self.atts['author'].get_att(id_col)
        new_author_ids = [id_val for id_val in author_ids if id_val != self.id]
        self.atts['author'].set_att(id_col, new_author_ids)
        self.atts['author'].pupdate_in_sqlite(sqlite)

class HNPost(HNSubmission, entities.Root):

    def pupdate_in_sqlite(self, sqlite):
        HNSubmission.pupdate_in_sqlite(self, sqlite, "post")

    def delete_from_sqlite(self, sqlite):
        HNSubmission.delete_from_sqlite(self, sqlite, "post")

    def get_prompt_str(self):
        return "POST: " + self.get_att("text")


class HNComment(HNSubmission, entities.Branch):

    def pupdate_in_sqlite(self, sqlite):
        HNSubmission.pupdate_in_sqlite(self, sqlite, "comment")

    
    def delete_from_sqlite(self, sqlite):
        HNSubmission.delete_from_sqlite(self, sqlite, "comment")

    def get_prompt_str(self):
        return "COMMENT: " + self.get_att("text")
