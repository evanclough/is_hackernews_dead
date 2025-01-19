"""
    A collection of utilites for retrieving and modifying data from the sqlite datasets
    created in the data module.
"""

import sqlite3
import json
import classes
import functools

import utils

"""
    Create a connection to the sqlite database, given its path.
"""
def connect_to_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    return (cursor, conn)

"""
    Run a selection query on a given table.
"""
def run_selection_query(cursor, table, query, contents_tuple=()):
    if len(contents_tuple) == 0:
        cursor.execute(query)
    else:
        cursor.execute(query, contents_tuple)

    content_tuples = cursor.fetchall()

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
def run_insertion_query(cursor, conn, table, contents_tuple, ignore_dups=False):
    atts = {
        "userProfiles": ["username", "about", "karma", "created", "userClass", "postIDs", "commentIDs", "favoritePostIDs", "textSamples", "interests", "beliefs", "miscJson"],
        "posts": ["by", "id", "score", "time", "title", "text", "url", "urlContent", "miscJson"],
        "comments": ["by", "id", "time", "text", "miscJson"]
    }

    query = f"""
        INSERT {'OR IGNORE' if ignore_dups else ''} INTO {table} ({', '.join(atts[table])})
        VALUES ({', '.join(['?' for att in atts[table]])})
    """

    cursor.executemany(query, contents_tuple)

    conn.commit()

"""
    Run an update query on a given table
"""
def run_update_query(cursor, conn, table, update_dict, item_to_update):
    update_att_str = functools.reduce(lambda acc, s: acc + s, [f"{att} = ?," for att in list(update_dict.keys())], "")[:-1]

    update_query = f"""
        UPDATE {table}
        SET {update_att_str}
        WHERE {'username' if table == 'userProfiles' else 'id'} = ?
    """

    cursor.execute(update_query, tuple(update_dict.values()) + (item_to_update,))

    conn.commit()

"""
    Run a delete query on a given table
"""
def run_delete_query(cursor, conn, table, where_dict):
    delete_att_str = functools.reduce(lambda acc, s: acc + s, [f"{att} = ?," for att in list(where_dict.keys())], "")[:-1]

    delete_query = f"""
        DELETE FROM {table} WHERE {delete_att_str}
    """

    cursor.execute(delete_query, tuple(where_dict.values()))

    conn.commit()

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
    Initialize and return a user profile object from the sqlite database, given a username.
"""
def get_user_profile(cursor, username):
    result = run_selection_query(cursor, "userProfiles", "SELECT * FROM userProfiles WHERE username = ?", (username,))
    if len(result) == 0:
        raise UniqueDBItemNotFound(f"Username {username} could not be found in the sqlite database")
    if len(result) > 1:
        raise MultipleUniqueItemsFound(f"Multiple users found with username {username}, this should never happen but just in case")
    return result[0]

"""
    Initialize and return a post object from the sqlite database, given an id.
"""
def get_post(cursor, post_id):
    result = run_selection_query(cursor, "posts", 'SELECT * FROM posts WHERE id = ?', (post_id, ))
    if len(result) == 0:
        raise UniqueDBItemNotFound(f"Post with id {post_id} could not be found in the sqlite database")
    if len(result) > 1:
        raise MultipleUniqueItemsFound(f"Multiple posts found with id {post_id}, this should never happen but just in case")
    return result[0]

"""
    Initialiez and return a comment object from the sqlite database, given an id.
"""
def get_comment(cursor, comment_id):
    result = run_selection_query(cursor,  "comments", 'SELECT * FROM comments WHERE id = ?', (comment_id, ))
    if len(result) == 0:
        raise UniqueDBItemNotFound(f"Comment with id {comment_id} could not be found in the sqlite database")
    if len(result) > 1:
        raise MultipleUniqueItemsFound(f"Multiple posts found with id {post_id}, this should never happen but just in case")
    return result[0]

    
"""
    Add a list of post ids to a user's record.
"""
def add_post_ids_to_user(cursor, conn, username, post_ids):
    user_profile = get_user_profile(cursor, username)
    updated_post_ids = [*user_profile.post_ids, *post_ids]
    update_dict = {"postIDs": json.dumps(updated_post_ids)}

    run_update_query(cursor, conn, "userProfiles", update_dict, username)


"""
    Add a list of comment ids to a user's record.
"""
def add_comment_ids_to_user(cursor, conn, username, comment_ids):
    user_profile = get_user_profile(cursor, username)
    updated_comment_ids = [*user_profile.comment_ids, *comment_ids]
    update_dict = {"commentIDs": json.dumps(updated_comment_ids)}

    run_update_query(cursor, conn, "userProfiles", update_dict, username)

"""
    Remove a list of post ids from a user's record
"""
def remove_post_ids_from_user(cursor, conn, username, post_ids):
    user_profile = get_user_profile(cursor, username)
    updated_comment_ids = [pid for pid in user_profile.post_ids if not (pid in post_ids)]
    update_dict = {"postIDs": json.dumps(updated_post_ids)}

    run_update_query(cursor, conn, userProfiles, update_dict, username)

"""
    Remove a list of comment ids from a user's record
"""
def remove_comment_ids_from_user(cursor, conn, username, comment_ids):
    user_profile = get_user_profile(cursor, username)
    updated_comment_ids = [cid for cid in user_profile.comment_ids if not (cid in comment_ids)]
    update_dict = {"commentIDs": json.dumps(updated_comment_ids)}

    run_update_query(cursor, conn, userProfiles, update_dict, username)


"""
    Add a list of user profiles to the database,
    and add all of their usernames to the usernames.json file.
"""

def insert_user_profiles(cursor, conn, dataset_path, user_dict_list, check_submission_history=False):
    user_profile_tuples = []
    new_username_list = utils.read_json(dataset_path + "usernames.json")

    for user_dict in user_dict_list:
        if check_submission_history:
            for post_id in [*user_dict["post_ids"], *user_dict["favorite_post_ids"]]:
                try:
                    get_post(cursor, post_id)
                except Exception as e:
                    print(f"Error adding user {username} to the database: post with id {post_id} in their history/favorites does not exist in the dataset.")
                
            for comment_id in user_dict["comment_ids"]:
                try:
                    get_comment(cursor, comment_id)
                except Exception as e:
                    print(f"Error adding user {username} to the database: comment with id {comment_id} in their history/favorites does not exist in the dataset.")
        
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
        new_username_list.append(user_dict["username"])
    
    try:
        run_insertion_query(cursor, conn, "userProfiles", user_profile_tuples)
        utils.write_json(new_username_list, dataset_path + "usernames.json")

        print("Successfully added user profiles: ")
        for user_dict in user_dict_list:
            print(user_dict["username"])
        print("to the dataset.")

        return True
    except Exception as e:
        print("Error adding user profiles to the dataset:")
        print(e)
        print("Skipping.")
        return False

"""
    Add a list of posts to the database.
"""
def insert_posts(cursor, conn, dataset_path, post_dict_list):
    post_tuples = []
    new_cs_dicts = utils.read_json(dataset_path + "contentStringLists.json")
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
        new_cs_dicts.append({"id": post_dict["id"], "kids": []})

    try:
        run_insertion_query(cursor, conn, "posts", post_tuples)
        for post_dict in post_dict_list:
            add_post_ids_to_user(cursor, conn, post_dict["by"], [post_dict["id"]])
        utils.write_json(new_cs_dicts, dataset_path + "contentStringLists.json")

        print("Successfully added posts: ")
        for post_dict in post_dict_list:
            print(post_dict["id"])
        print("to the dataset.")

        return True
    except Exception as e:
        print("Error adding posts to the dataset:")
        print(e)
        print("Skipping.")
        return False
    

"""
    Add a list of comments to the database.
"""
def insert_comments(cursor, conn, comment_dict_list):
    comment_tuples = []
    for comment_dict in comment_dict_list:
        comment_tuples.append((
            comment_dict["by"],
            comment_dict["id"],
            str(comment_dict["time"]),
            comment_dict["text"],
            json.dumps(comment_dict["misc_json"])
        ))

    try:
        run_insertion_query(cursor, conn, "comments", comment_tuples)
        for comment_dict in comment_dict_list:
            add_comment_ids_to_user(cursor, conn, comment_dict["by"], [comment_dict["id"]])

        print("Successfully added comments: ")
        for comment_dict in comment_dict_list:
            print(comment_dict["id"])
        print("to the database.")

        return True
    except Exception as e:
        print("Error adding comments to the database:")
        print(e)
        print("Skipping.")
        return False

"""
    Remove a list of items from the database.
"""
def remove_items(cursor, conn, table, item_list):
    key_to_delete = ("username" if table == "userProfiles" else "id")
    [run_delete_query(cursor, conn, table, {key_to_delete: item}) for item in item_list]