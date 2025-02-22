import sqlite3
import json
import functools

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
    def __init__(self, db_path, base_attributes, features, create=False):
        self.db_path = db_path
        self.base_attributes = base_attributes

        self.item_types = {}
        for base_attribute in base_attributes:
            if base_attribute["identifier"]:
                self.item_types[base_attribute["item_type"]] = {
                    "primary_key": base_attribute["name"]
                }

        self.py_to_sql = {
            "list(int)TEXT": lambda l: json.dumps(l),
            "list(str)TEXT": lambda l: json.dumps(l),
            "intTEXT": lambda i: str(i),
            "intINTEGER": lambda i: i,
            "strTEXT": lambda s: s,
            "strINTEGER": lambda s: int(s)
        }

        self.sql_to_py = {
            "TEXTlist(int)": lambda l: json.loads(l),
            "TESTlist(str)": lambda l: json.loads(l),
            "TEXTint": lambda s: int(set_base_attributes),
            "INTEGERint": lambda i: i,
            "TEXTstr": lambda s: s,
            "INTEGERstr": lambda i: str(i)
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

        item_type_atts = [att for att in self.attributes if att['item_type'] == item_type]
        sorted_item_type_atts = sorted(item_type_atts, key=lambda a: a['sqlite_order'])
        conversions = [self.sql_to_py[f"{att['sqlite_type']}{att['py_type']}"] for att in sorted_item_type_atts]
        converted_results = [[conv(att) for att, conv in list(zip(list(row_tuple), conversions))] for row_tuple in row_tuples]
        
        return converted_results
    
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
        Run an update query on an item in a given item type's table, given an update dict, and an identifier
    """
    @_with_db
    def update_item_type(self, item_type, identifier, update_dict):
        update_att_str = ", ".join([f"{att} = ?" for att in list(update_dict.keys())])

        update_query = f"""
            UPDATE {item_type}
            SET {update_att_str}
            WHERE {self.item_types[item_type]['primary_key']} = ?
        """

        self.cursor.execute(update_query, tuple(update_dict.values()) + (identifier,))

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
        Get a row for a given item type with a given identifier.
    """
    def get_item_row_by_identifier(self, item_type, identifier):
        identifier_name = self.item_types[item_type]['primary_key']

        where_dict = {identifier_name: identifier}

        result = self.select_item_type(item_type, where_dict)

        if len(result) == 0:
            raise UniqueDBItemNotFound(f"Item of type {item_type} with identifier {identifier} could not be found in the sqlite database.")
        if len(result) > 1:
            raise MultipleUniqueItemsFound(f"Item of type {item_type} with identifier {identifier} had multiple results found. this should never happen but just in case")
        

        return result[0]

    """
        Remove a list of items from a given item type's table, given a list of identifiers
    """
    def delete_items_by_identifier_list(self, item_type, identifier_list):
        identifier_name = self.item_types[item_type]['primary_key']

        for identifier in identifier_list:
            where_dict = {identifier_name: identifier}
            self.delete_item_type(item_type, where_dict)
