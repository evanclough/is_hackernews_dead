import sqlite3
import json
import functools
import classes

import utils


"""
    To be raised if a unique database item isn't found
"""
class UniqueDBItemNotFound(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

"""
    To be raised if somehow multiple supposedly unique items are found,
    this shouldn't happen ever but i like being thorough
"""
class MultipleUniqueItemsFound(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

"""
    For general insertion errors
"""
class InsertionError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

"""
    A class to hold all methods used to access the database.
"""
class SqliteDB:
    def __init__(self, db_path):
        self.db_path = db_path

    def _with_db(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with sqlite3.connect(self.db_path) as conn:
                self.conn = conn
                self.cursor = conn.cursor()
                return func(self, *args, **kwargs)
        return wrapper

    """
        Run a selection query on a given table.
    """
    @_with_db
    def _run_selection_query(self, table, query, contents_tuple=()):
        if len(contents_tuple) == 0:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, contents_tuple)

        content_tuples = self.cursor.fetchall()

        table_classes = {
            "userProfiles": classes.UserProfile,
            "posts": classes.Post,
            "comments": classes.Comment
        }
        
        contents = [table_classes[table](sqlite_row=content_tuple) for content_tuple in content_tuples]

        return contents
    
    """
        Run an insertion query on a given table
    """
    @_with_db
    def _run_insertion_query(self, table, contents_tuple, ignore_dups=False):
        atts = {
            "userProfiles": ["username", "about", "karma", "created", "userClass", "postIDs", "commentIDs", "favoritePostIDs", "textSamples", "interests", "beliefs", "miscJson"],
            "posts": ["by", "id", "score", "time", "title", "text", "url", "urlContent", "miscJson"],
            "comments": ["by", "id", "time", "text", "miscJson"]
        }

        query = f"""
            INSERT {'OR IGNORE' if ignore_dups else ''} INTO {table} ({', '.join(atts[table])})
            VALUES ({', '.join(['?' for att in atts[table]])})
        """

        self.cursor.executemany(query, contents_tuple)

        self.conn.commit()

    """
        Run an update query on a given table
    """
    @_with_db
    def _run_update_query(self, table, update_dict, item_to_update):
        update_att_str = functools.reduce(lambda acc, s: acc + s, [f"{att} = ?," for att in list(update_dict.keys())], "")[:-1]

        update_query = f"""
            UPDATE {table}
            SET {update_att_str}
            WHERE {'username' if table == 'userProfiles' else 'id'} = ?
        """

        self.cursor.execute(update_query, tuple(update_dict.values()) + (item_to_update,))

        self.conn.commit()

    """
        Run a delete query on a given table
    """
    @_with_db
    def _run_delete_query(self, table, where_dict):
        delete_att_str = functools.reduce(lambda acc, s: acc + s, [f"{att} = ?," for att in list(where_dict.keys())], "")[:-1]

        delete_query = f"""
            DELETE FROM {table} WHERE {delete_att_str}
        """

        self.cursor.execute(delete_query, tuple(where_dict.values()))

        self.conn.commit()

    """
        Initialize and return a user profile object from the sqlite database, given a username.
    """
    def get_user_profile(self, username):
        result = self._run_selection_query("userProfiles", "SELECT * FROM userProfiles WHERE username = ?", (username,))
        if len(result) == 0:
            raise UniqueDBItemNotFound(f"Username {username} could not be found in the sqlite database")
        if len(result) > 1:
            raise MultipleUniqueItemsFound(f"Multiple users found with username {username}, this should never happen but just in case")
        return result[0]

    """
        Initialize and return a post object from the sqlite database, given an id.
    """
    def get_post(self, post_id):
        result = self._run_selection_query("posts", 'SELECT * FROM posts WHERE id = ?', (post_id, ))
        if len(result) == 0:
            raise UniqueDBItemNotFound(f"Post with id {post_id} could not be found in the sqlite database")
        if len(result) > 1:
            raise MultipleUniqueItemsFound(f"Multiple posts found with id {post_id}, this should never happen but just in case")
        return result[0]

    """
        Initialiez and return a comment object from the sqlite database, given an id.
    """
    def get_comment(self, comment_id):
        result = self._run_selection_query("comments", 'SELECT * FROM comments WHERE id = ?', (comment_id, ))
        if len(result) == 0:
            raise UniqueDBItemNotFound(f"Comment with id {comment_id} could not be found in the sqlite database")
        if len(result) > 1:
            raise MultipleUniqueItemsFound(f"Multiple posts found with id {post_id}, this should never happen but just in case")
        return result[0]

    """
        Add a list of post ids to a user's record.
    """
    def add_post_ids_to_user(self, username, post_ids):
        user_profile = self.get_user_profile(username)
        updated_post_ids = [*user_profile.post_ids, *post_ids]
        update_dict = {"postIDs": json.dumps(updated_post_ids)}

        self._run_update_query("userProfiles", update_dict, username)


    """
        Add a list of comment ids to a user's record.
    """
    def add_comment_ids_to_user(self, username, comment_ids):
        user_profile = self.get_user_profile(username)
        updated_comment_ids = [*user_profile.comment_ids, *comment_ids]
        update_dict = {"commentIDs": json.dumps(updated_comment_ids)}

        self._run_update_query("userProfiles", update_dict, username)

    """
        Remove a list of post ids from a user's record
    """
    def remove_post_ids_from_user(self, username, post_ids):
        user_profile = self.get_user_profile(username)
        updated_post_ids = [pid for pid in user_profile.post_ids if not (pid in post_ids)]
        update_dict = {"postIDs": json.dumps(updated_post_ids)}

        self._run_update_query("userProfiles", update_dict, username)

    """
        Remove a list of comment ids from a user's record
    """
    def remove_comment_ids_from_user(self, username, comment_ids):
        user_profile = self.get_user_profile(username)
        updated_comment_ids = [cid for cid in user_profile.comment_ids if not (cid in comment_ids)]
        update_dict = {"commentIDs": json.dumps(updated_comment_ids)}

        self._run_update_query("userProfiles", update_dict, username)

    """
        Add a list of user profiles to the database,
        and add all of their usernames to the usernames.json file.
    """

    def insert_user_profiles(self, user_dict_list, check_submission_history=False):
        user_profile_tuples = []

        for user_dict in user_dict_list:
            if check_submission_history:
                for post_id in [*user_dict["post_ids"], *user_dict["favorite_post_ids"]]:
                    try:
                        self.get_post(post_id)
                    except Exception as e:
                        raise InsertionError(f"Error adding user {username} to the database: post with id {post_id} in their history/favorites does not exist in the dataset.")
                    
                for comment_id in user_dict["comment_ids"]:
                    try:
                        self.get_comment(comment_id)
                    except Exception as e:
                        raise InsertionError(f"Error adding user {username} to the database: post with id {post_id} in their history/favorites does not exist in the dataset.")
            
            user_profile_tuples.append((
                user_dict["username"],
                user_dict["about"],
                user_dict["karma"],
                str(user_dict["created"]),
                user_dict["user_class"],
                json.dumps(user_dict["post_ids"]),
                json.dumps(user_dict["comment_ids"]),
                json.dumps(user_dict["favorite_post_ids"]),
                json.dumps(user_dict["text_samples"]),
                json.dumps(user_dict["interests"]),
                json.dumps(user_dict["beliefs"]),
                json.dumps(user_dict["misc_json"])
            ))
        
        self._run_insertion_query("userProfiles", user_profile_tuples)

    """
        Add a list of posts to the database.
    """
    def insert_posts(self, post_dict_list):
        post_tuples = []
        for post_dict in post_dict_list:
            post_tuples.append((
                post_dict["by"],
                post_dict["id"],
                post_dict["score"],
                str(post_dict["time"]),
                post_dict["title"],
                post_dict["text"],
                post_dict["url"],
                post_dict["url_content"],
                json.dumps(post_dict["misc_json"])
            ))

        self._run_insertion_query("posts", post_tuples)
        for post_dict in post_dict_list:
            self.add_post_ids_to_user(post_dict["by"], [post_dict["id"]])

    """
        Add a list of comments to the database.
    """
    def insert_comments(self, comment_dict_list):
        comment_tuples = []
        for comment_dict in comment_dict_list:
            comment_tuples.append((
                comment_dict["by"],
                comment_dict["id"],
                str(comment_dict["time"]),
                comment_dict["text"],
                json.dumps(comment_dict["misc_json"])
            ))

        self._run_insertion_query("comments", comment_tuples)
        for comment_dict in comment_dict_list:
            self.add_comment_ids_to_user(comment_dict["by"], [comment_dict["id"]])


    """
        Remove a list of items from the database.
    """
    def remove_items(self, table, item_list):
        key_to_delete = ("username" if table == "userProfiles" else "id")
        [self._run_delete_query(table, {key_to_delete: item}) for item in item_list]



if __name__ == "__main__":
    root_dataset_path = utils.fetch_env_var("ROOT_DATASET_PATH")
    db_path = root_dataset_path + "CURRENT_TEST/data.db"
    db = SqliteDB(db_path)
    test = db.get_user_profile("test_username888888")
    print(test)
