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
    def __init__(self, db_path, features, create=False):
        self.db_path = db_path
        self.item_types = {
            "users": {
                "primary_key": "username"
            },
            "posts": {
                "primary_key": "id"
            },
            "comments": {
                "primary_key": "id"
            }
        }
        self.base_attributes = [
            {
                "item_type": "users",
                "name": "username",
                "sqlite_type": "TEXT",
                "sqlite_order": 0,
                "py_type": "str"
            },
            {
                "item_type": "users",
                "name": "about",
                "sqlite_type": "TEXT",
                "sqlite_order": 1,
                "py_type": "str"
            },
            {
                "item_type": "users",
                "name": "karma",
                "sqlite_type": "INTEGER",
                "sqlite_order": 2,
                "py_type": "int"
            },
            {
                "item_type": "users",
                "name": "created",
                "sqlite_type": "INTEGER",
                "sqlite_order": 3,
                "py_type": "int"
            },
            {
                "item_type": "users",
                "name": "user_class",
                "sqlite_type": "TEXT",
                "sqlite_order": 4,
                "py_type": "str"
            },
            {
                "item_type": "users",
                "name": "post_ids",
                "sqlite_type": "TEXT",
                "sqlite_order": 5,
                "py_type": "list(int)"
            },
            {
                "item_type": "users",
                "name": "comment_ids",
                "sqlite_type": "TEXT",
                "sqlite_order": 6,
                "py_type": "list(int)"
            },
            {
                "item_type": "users",
                "name": "favorite_post_ids",
                "sqlite_type": "TEXT",
                "sqlite_order": 7,
                "py_type": "list(int)"
            },
            {
                "item_type": "posts",
                "name": "by",
                "sqlite_type": "TEXT",
                "sqlite_order": 0,
                "py_type": "str"
            },
            {
                "item_type": "posts",
                "name": "id",
                "sqlite_type": "INTEGER",
                "sqlite_order": 1,
                "py_type": "int"
            },
            {
                "item_type": "posts",
                "name": "score",
                "sqlite_type": "INTEGER",
                "sqlite_order": 2,
                "py_type": "int"
            },
            {
                "item_type": "posts",
                "name": "time",
                "sqlite_type": "INTEGER",
                "sqlite_order": 3,
                "py_type": "int"
            },
            {
                "item_type": "posts",
                "name": "title",
                "sqlite_type": "TEXT",
                "sqlite_order": 4,
                "py_type": "str"
            },
            {
                "item_type": "posts",
                "name": "text",
                "sqlite_type": "TEXT",
                "sqlite_order": 5,
                "py_type": "str"
            },
            {
                "item_type": "posts",
                "name": "url",
                "sqlite_type": "TEXT",
                "sqlite_order": 6,
                "py_type": "str"
            },
            {
                "item_type": "posts",
                "name": "url_content",
                "sqlite_type": "TEXT",
                "sqlite_order": 7,
                "py_type": "str"
            },
            {
                "item_type": "comments",
                "name": "by",
                "sqlite_type": "TEXT",
                "sqlite_order": 0,
                "py_type": "str"
            },
            {
                "item_type": "comments",
                "name": "id",
                "sqlite_type": "INTEGER",
                "sqlite_order": 1,
                "py_type": "int"
            },
            {
                "item_type": "comments",
                "name": "text",
                "sqlite_type": "TEXT",
                "sqlite_order": 2,
                "py_type": "str"
            },
            {
                "item_type": "comments",
                "name": "time",
                "sqlite_type": "INTEGER",
                "sqlite_order": 3,
                "py_type": "int"
            },
            {
                "item_type": "comments",
                "name": "parent",
                "sqlite_type": "INTEGER",
                "sqlite_order": 4,
                "py_type": "int"
            }   
        ]

        self.py_to_sql = {
            "list(int)TEXT": lambda l: json.dumps(l),
            "list(str)TEXT": lambda l: json.dumps(l),
            "intTEXT": lambda i: str(i),
            "intINTEGER": lambda i: i,
            "strTEXT": lambda i: i,
            "strINT": lambda s: int(s)
        }

        self.attributes = self.base_attributes + features

        if create:
            self._create()


    def _with_db(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with sqlite3.connect(self.db_path) as conn:
                self.conn = conn
                self.cursor = conn.cursor()
                return func(self, *args, **kwargs)
        return wrapper


    """
        Create the sqlite database and the needed tables at the specified path.
    """
    @_with_db
    def _create(self):
        for item_type_name, item_type_dict in self.item_types.items():
            create_table_query = f"CREATE TABLE {item_type_name} (" + "\n"
            attribute_list = [
                f"{att['name']} {att['sqlite_type']} {'PRIMARY KEY' if item_type_dict['primary_key'] == att['name'] else ''}"
                for i, att in enumerate(self.attributes)
                if att["item_type"] == item_type_name
            ]
            create_table_query += ', \n'.join(attribute_list)
            create_table_query += "\n);"
            self.cursor.execute(create_table_query)
        
        self.conn.commit()

    """
        Run a given selection query on a given item types table, given a where dict.
    """
    @_with_db
    def select_item_type(self, item_type, where_dict):
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])

        select_query = f"""
            SELECT * FROM {item_type} WHERE {where_str}
        """

        self.cursor.execute(select_query, tuple(where_dict.values()))

        row_tuples = self.cursor.fetchall()

        return row_tuples
    
    """
        Insert some items to a given item type's table, given a list of item dicts
    """
    @_with_db
    def insert_item_type(self, item_type, item_dict_list, ignore_dups=False):

        item_type_atts = [att for att in self.attributes if att['item_type'] == item_type]
        for att in item_type_atts:
            att["conversion"] = self.py_to_sql[f"{att['py_type']}{att['sqlite_type']}"]
        sorted_item_type_atts = sorted(item_type_atts, key=lambda a: a['sqlite_order'])
        item_row_tuples = [tuple([item_type_att['conversion'](item_dict[item_type_att['name']]) for item_type_att in sorted_item_type_atts]) for item_dict in item_dict_list]

        insertion_query = f"""
            INSERT {'OR IGNORE' if ignore_dups else ''} 
            INTO {item_type} 
            ({', '.join([a['name'] for a in item_type_atts])})
            VALUES ({', '.join(['?' for a in item_type_atts])})
        """

        self.cursor.executemany(insertion_query, item_row_tuples)

        self.conn.commit()

    """
        Run an update query on an item in a given item type's table, given an update dict, and a primary key
    """
    @_with_db
    def update_item_type(self, item_type, primary_key, update_dict):
        update_att_str = ", ".join([f"{att} = ?" for att in list(update_dict.keys())])

        update_query = f"""
            UPDATE {item_type}
            SET {update_att_str}
            WHERE {self.item_types[item_type]['primary_key']} = ?
        """

        self.cursor.execute(update_query, tuple(update_dict.values()) + (primary_key,))

        self.conn.commit()

    """
        Run a delete query on a given item type's table
    """
    @_with_db
    def delete_item_type(self, item_type, where_dict):
        delete_att_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])

        delete_query = f"""
            DELETE FROM {item_type} WHERE {delete_att_str}
        """

        self.cursor.execute(delete_query, tuple(where_dict.values()))

        self.conn.commit()

    """
        Get a row for a given item type with a given primary key.
    """
    def get_item_row_by_pk(self, item_type, primary_key):
        primary_key_name = self.item_types[item_type]['primary_key']

        where_dict = {primary_key_name: primary_key}

        result = self.select_item_type(item_type, where_dict)

        if len(result) == 0:
            raise UniqueDBItemNotFound(f"Item of type {item_type} with primary key {primary_key} could not be found in the sqlite database.")
        if len(result) > 1:
            raise MultipleUniqueItemsFound(f"Item of type {item_type} with primary key {primary_key} had multiple results found. this should never happen but just in case")
        return result[0]

    """
        Remove a list of items from a given item type's table, given a list of primary keys
    """
    def delete_items_by_pk(self, item_type, primary_key_list):
        primary_key_name = self.item_types[item_type]['primary_key']

        for primary_key in primary_key_list:
            where_dict = {primary_key_name: primary_key}
            self.delete_item_type(item_type, where_dict)
