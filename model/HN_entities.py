import entities

from chroma_db import EmbeddingsNotFoundError

class HNUserLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)

class HNUserStoreError(Exception):
    def __init__(self, message):
        super().__init__(message)


class HNUser(entities.User):

    model = entities.EntityModel(
        "username",
        "users",
        entities.AttClassModel([
            entities.SqliteAttModel("username", False, False, "str", "TEXT"),
            entities.SqliteAttModel("about", True, True, "str", "TEXT"),
            entities.SqliteAttModel("karma", False, True, "int", "INTEGER"),
            entities.SqliteAttModel("created", False, True, "int", "INTEGER"),
            entities.SqliteAttModel("user_class", False, False, "str", "TEXT"),
            entities.SqliteAttModel("post_ids", False, False, "dict", "TEXT"),
            entities.SqliteAttModel("comment_ids", False, False, "dict", "TEXT"),
            entities.SqliteAttModel("favorite_post_ids", False, False, "dict", "TEXT")
        ]),
        entities.AttClassModel([
            entities.DerivedAttModel("comments", False, False, "list(entity)", lambda a, b, c: a),
            entities.DerivedAttModel("posts", False, False, "list(entity)", lambda a, b, c: a),
            entities.DerivedAttModel("favorite_posts", False, False, "list(entity)", lambda a, b, c: a)
        ]),
        entities.AttClassModel([])
    )

    def load_submission_history(sub_type, base, derived, generated):
        submission_types = {
            "posts": {
                "id_list": "post_ids",
                "init_func": HNPost
            },
            "comments": {
                "id_list": "comment_ids",
                "init_func": HNComment
            },
            "favorite_posts": {
                "id_list": "favorite_post_ids",
                "init_func": HNPost
            }
        }
        id_list = self.base.get_value(submission_types[sub_type]["id_list"])
        submission_list = []
        for id_val in id_list:
            try:
                submission = submission_types[sub_type]['init_func'](id_val, self.sqlite, self.chroma)
                submission_list.append(submission)
            except Exception as e:
                    self._print(f"Error in retrieving {sub_type} {id_val} in submission history of {self}.")
                    if skip_submission_errors:
                        self._print("Skipping...")
                        continue
                    else:
                        raise e
        return submission_list

    """

    def pupdate_in_chroma(self, embed_sub_his=False):
        super().pupdate_in_chroma()
        sub_types = ['posts', 'comments', 'favorite_posts']
        if embed_sub_his:
            for sub_type in sub_types:
                for submission_object in self.atts[sub_type]:
                    submission_object.pupdate_in_chroma()

    def delete_from_chroma(self, delete_sub_his=False):
        super().delete_from_chroma()
        sub_types = ['posts', 'comments', 'favorite_posts']
        if delete_sub_his:
            for sub_type in sub_types:
                for submission_object in self.atts[sub_type]:
                    submission_object.delete_from_chroma()

    def load_derived_atts(self, post_factory=None, comment_factory=None, skip_submission_errors=False):
        
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

    def load_derived_embeddings(self, sub_att_classes):
        sub_types = ['posts', 'comments', 'favorite_posts']
        for sub_type in sub_types:
            for submission in self.atts[sub_type]:
                for att_class in sub_att_classes:
                    submission.load_from_chroma(att_class)
    """


class HNSubmissionLoader(entities.DerivedLoader):
    def __init__(self, user_factory=None, load_author_submission_history=False, author_att_classes=[], **kwargs):
        super().__init__(**kwargs)

        self.att_params['user_factory'] = user_factory
        self.att_params['load_author_submission_history'] = load_author_submission_history
        self.embedding_params['author_att_classes'] = author_att_classes

class HNSubmission(entities.Submission):

    """
    def pupdate_in_chroma(self, embed_author=False):
        super().pupdate_in_chroma()
        if embed_author:
            self.atts['author'].pupdate_in_chroma()

    def delete_from_chroma(self, delete_author=False):
        super().pupdate_in_chroma()
        if delete_author:
            self.atts['author'].delete_from_chroma()

    def load_derived_atts(self, user_factory=None, load_author_submission_history=False):
        self._print(f"Loading author of {self}...")

        if user_factory != None:
            self.atts['author'] = user_factory(self.get_att("by"))
        
        self._print(f"Successfully loaded author of {self}.")

    def load_derived_embeddings(self, author_att_classes):
        self._print(f"Loading embeddings for author of {self}...")

        for att_class in author_att_classes:
            self.atts['author'].load_from_chroma(att_class)

        self._print(f"Loaded embeddings for author of {self}.")

    def add_to_author_history(self, sub_type):

        if self.atts['author'] == None:
            raise HNSubmissionStoreError(f"Error: attempted to update {self} in sqlite, but author is not loaded.")

        id_col = "post_ids" if sub_type == "post" else "comment_ids"
        author_ids = self.atts['author'].get_att(id_col)
        if not (self.id in author_ids):
            self.atts['author'].set_att(id_col, [*author_ids, self.id])
            self.atts['author'].pupdate_in_sqlite()

    def remove_from_author_history(self, sub_type):

        if self.atts['author'] == None:
            raise HNSubmissionStoreError(f"Error: attempted to remove {self} from sqlite, but author is not loaded.")

        id_col = "post_ids" if sub_type == "post" else "comment_ids"
        author_ids = self.atts['author'].get_att(id_col)
        new_author_ids = [id_val for id_val in author_ids if id_val != self.id]
        self.atts['author'].set_att(id_col, new_author_ids)
        self.atts['author'].pupdate_in_sqlite()

    def get_time(self):
        return self.get_att("time")
    """

class HNPost(HNSubmission, entities.Root):

    model = entities.EntityModel(
        "id",
        "posts",
        entities.AttClassModel([
            entities.SqliteAttModel("by", False, False, "str", "TEXT"),
            entities.SqliteAttModel("id", False, False, "int", "INTEGER"),
            entities.SqliteAttModel("score", False, True, "int", "INTEGER"),
            entities.SqliteAttModel("time", False, True, "int", "INTEGER"),
            entities.SqliteAttModel("title", False, False, "str", "TEXT"),
            entities.SqliteAttModel("text", False, False, "str", "TEXT"),
            entities.SqliteAttModel("url", False, False, "str", "TEXT"),
            entities.SqliteAttModel("url_content", False, False, "str", "TEXT"),
        ]),
        entities.AttClassModel([
            entities.DerivedAttModel("author", False, False, "entity", lambda a, b, c: a),
            entities.DerivedAttModel("full_content", True, True, "str", lambda a, b, c: a),
        ]),
        entities.AttClassModel([
            entities.GeneratedAttModel("url_content_summary", False, False, "str", "TEXT", "This is the body of an HTML web page. {{url_content}} Can you please give a summary of its contents in 500 characters or less?")
        ])
    )

    """
    def add_to_author_history(self):
        HNSubmission.add_to_author_history(self, "post")

    def remove_from_author_history(self):
        HNSubmission.remove_from_author_history(self, "post")

    def load_derived_atts(self, user_factory=None, load_author_submission_history=False):

        super().load_derived_atts(user_factory=user_factory, load_author_submission_history=load_author_submission_history)

        self.atts['full_content'] = f"TITLE: {self.atts['title']}" + "\n"
        if self.atts['text'] != '':
            self.atts['full_content'] += f"BODY TEXT: {self.atts['text']}" + "\n"
        if self.atts['url_content'] != '':
            self.atts['full_content'] += f"URL CONTENT SUMMARY: {self.atts['url_content_summary']}"

    def load_derived_embeddings(self, author_att_classes):
        super().load_derived_embeddings(author_att_classes)

        att_model = [att_model for att_model in self.entity_model['attributes']['derived'] if att_model['name'] == 'full_content'][0]
        embeddings = self.chroma.retrieve(self.entity_model, att_model, self.id)
        self.embeddings[att_model['name']] = embeddings['embeddings']        

    def get_prompt_str(self):
        return "POST: " + self.get_att("text")
    """


class HNComment(HNSubmission, entities.Stem):

    model = entities.EntityModel(
        "id",
        "comments",
        entities.AttClassModel([
            entities.SqliteAttModel("by", False, False, "str", "TEXT"),
            entities.SqliteAttModel("id", False, False, "int", "INTEGER"),
            entities.SqliteAttModel("time", False, True, "int", "INTEGER"),
            entities.SqliteAttModel("text", True, True, "str", "TEXT"),
        ]),
        entities.AttClassModel([
            entities.DerivedAttModel("author", False, False, "entity", lambda a, b ,c: a),
        ]),
        entities.AttClassModel([])
    )

    def __str__(self):
        contents = f"Comment with id {self.id}"
        return contents
    """

    def add_to_author_history(self):
        HNSubmission.add_to_author_history(self, "comment")
    
    def remove_from_author_history(self):
        HNSubmission.remove_from_author_history(self, "comment")


    def get_prompt_str(self):
        return "COMMENT: " + self.get_att("text")
    """