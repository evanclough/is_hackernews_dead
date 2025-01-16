"""
    A collection of utilites for retrieving and modifying data from the sqlite datasets
    created in the data module.
"""

import sqlite3
import json
import classes

import utils

"""
    Create a cursor to the sqlite database, given its path.
"""
def create_sqlite_cursor(db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    return cursor

"""
    Run a select query on the user profiles table, and return the result.
"""
def run_user_profile_selection_query(cursor, query, contents_tuple=()):
    if len(contents_tuple) == 0:
        cursor.execute(query)
    else:
        cursor.execute(query, contents_tuple)
    user_profile_tuples = cursor.fetchall()
    user_profiles = []
    for user_profile_tuple in user_profile_tuples:
        user_profiles.append(classes.UserProfile(sqlite_row=user_profile_tuple))
    return user_profiles

"""
    Run a select query on the posts table, and return the result.
"""
def run_post_selection_query(cursor, query, contents_tuple=()):
    if len(contents_tuple) == 0:
        cursor.execute(query)
    else:
        cursor.execute(query, contents_tuple)
    post_tuples = cursor.fetchall()
    posts = []
    for post_tuple in post_tuples:
        posts.append(classes.Post(sqlite_row=post_tuple))
    return posts

"""
    Run a select query on the comments table, and return the result.
"""
def run_comment_selection_query(cursor, query, contents_tuple=()):
    if len(contents_tuple) == 0:
        cursor.execute(query)
    else:
        cursor.execute(query, contents_tuple)
    comment_tuples = cursor.fetchall()
    comments = []
    for comment_tuple in comment_tuples:
        comments.append(classes.Comment(sqlite_row=comment_tuple))
    return comments

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
    result = run_user_profile_selection_query(cursor, "SELECT * FROM userProfiles WHERE username = ?", (username,))
    if len(result) == 0:
        raise UniqueDBItemNotFound(f"Username {username} could not be found in the sqlite database")
    if len(result) > 1:
        raise MultipleUniqueItemsFound(f"Multiple users found with username {username}, this should never happen but just in case")
    return result[0]

"""
    Initialize and return a post object from the sqlite database, given an id.
"""
def get_post(cursor, post_id):
    result = run_post_selection_query(cursor, 'SELECT * FROM posts WHERE id = ?', (post_id, ))
    if len(result) == 0:
        raise UniqueDBItemNotFound(f"Post with id {post_id} could not be found in the sqlite database")
    if len(result) > 1:
        raise MultipleUniqueItemsFound(f"Multiple posts found with id {post_id}, this should never happen but just in case")
    return result[0]

"""
    Initialiez and return a comment object from the sqlite database, given an id.
"""
def get_comment(cursor, comment_id):
    result = run_comment_selection_query(cursor, 'SELECT * FROM comments WHERE id = ?', (comment_id, ))
    if len(result) == 0:
        raise UniqueDBItemNotFound(f"Comment with id {comment_id} could not be found in the sqlite database")
    if len(result) > 1:
        raise MultipleUniqueItemsFound(f"Multiple posts found with id {post_id}, this should never happen but just in case")
    return result[0]