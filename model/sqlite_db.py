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
    def __init__(self, path, entities, create=False):
        self.path = path
        self.entities = entities

        self.conversions = {
            "json_load": json.loads,
            "json_dump": json.dumps
        }

        self.get_conversion = lambda a: self.conversions[a] if a in self.conversions else (lambda b: b)

        if create:
            self._create()


    def _with_db(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with sqlite3.connect(self.path) as conn:
                self.conn = conn
                self.cursor = conn.cursor()
                return func(self, *args, **kwargs)
        return wrapper

    """
        Get all attributes for a given entity that are stored in sqlite, in given order.
    """
    def get_atts(self, entity_type):
        atts = self.entities[entity_type]['attributes']["base"] + self.entities[entity_type]['attributes']["generated"]
        sorted_atts = sorted(atts, key=lambda a: a['sqlite_order'])
        return sorted_atts

    """
        Create the sqlite database and the needed tables at the specified path.
    """
    @_with_db
    def _create(self):
        for entity_type, entity_dict in self.entities.items():
            atts = get_atts(entity_type)
            create_table_query = f"CREATE TABLE {entity_dict['table_name']} (" + "\n"
            att_strs = [
                f"{att['name']} {att['sqlite_type']} {'PRIMARY KEY' if entity_dict['id_att'] == att['name'] else ''}"
                for att in atts
            ]
            create_table_query += ', \n'.join(att_strs)
            create_table_query += "\n);"
            self.cursor.execute(create_table_query)
        
        self.conn.commit()

    """
        Run a given selection query on a given entity's table, given a where dict.
    """
    @_with_db
    def select(self, entity_type, where_dict):
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])

        select_query = f"""
            SELECT * FROM {self.entities[entity_type]['table_name']} WHERE {where_str}
        """

        self.cursor.execute(select_query, tuple(where_dict.values()))

        row_tuples = self.cursor.fetchall()

        atts = self.get_atts(entity_type)
        zipped_results = [list(zip(atts, list(row_tuple))) for row_tuple in row_tuples]
        converted_results = [[(att['name'], self.get_conversion(att['conversions']['load'])(val)) for att, val in r] for r in zipped_results]
        
        return converted_results
    
    """
        Insert some items to a given entity's table, given a list of item dicts
    """
    @_with_db
    def insert(self, entity_type, item_dict_list, ignore_dups=False):

        atts = self.get_entity_atts(entity_type)

        converted_item_lists = [
            [self.get_conversion(att['conversions']['store'])(item_dict[att["name"]]) for att in atts]
            for item_dict in item_dict_list]
        
        tuples_to_insert = [tuple(item_list) for item_list in converted_item_lists]

        insertion_query = f"""
            INSERT {'OR IGNORE' if ignore_dups else ''} 
            INTO {self.entities[entity]["table_name"]} 
            ({', '.join([att['name'] for att in entity_atts])})
            VALUES ({', '.join(['?' for att in entity_atts])})
        """

        self.cursor.executemany(insertion_query, tuples_to_insert)

        self.conn.commit()

    """
        Run an update query on an item in a given entity's table, given an update dict and a where dict 
    """
    @_with_db
    def update(self, entity_type, where_dict, update_dict):
        update_str = ", ".join([f"{att} = ?" for att in list(update_dict.keys())])
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])
        
        update_query = f"""
            UPDATE {self.entities[entity_type]['table_name']}
            SET {update_str}
            WHERE {where_str}
        """

        self.cursor.execute(update_query, tuple(update_dict.values(), where_dict.values()))

        self.conn.commit()

    """
        Run a delete query on a given entity's table
    """
    @_with_db
    def delete(self, entity_type, where_dict):
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])

        delete_query = f"""
            DELETE FROM {self.entities[entity_type]['table_name']} WHERE {where_str}
        """

        self.cursor.execute(delete_query, tuple(where_dict.values()))

        self.conn.commit()

    """
        Get a row for a given entity with a given id.
    """
    def get_by_id(self, entity_type, id_val):
        id_att = self.entities[entity_type]['id_att']

        where_dict = {id_att: id_val}

        result = self.select(entity_type, where_dict)

        if len(result) == 0:
            raise UniqueDBItemNotFound(f"Item of type {entity_type} with id {id_val} could not be found in the sqlite database.")
        if len(result) > 1:
            raise MultipleUniqueItemsFound(f"Item of type {entity_type} with id {id_val} had multiple results found. this should never happen but just in case")

        return result[0]

    """
        Remove a list of entities from a given entity's table, given a list of ids
    """
    def delete_by_id_list(self, entity_type, id_list):
        id_att = self.entities[entity_type]['id_att']

        for id_val in id_list:
            where_dict = {id_att: id_val}
            self.delete(entity_type, where_dict)

    """
        Update a list of entities given an update dict and a list of ids
    """
    def update_by_id(self, entity_type, id_val, update_dict):
        id_att = self.entities[entity_type]['id_att']

        where_dict = {id_att: id_val}
        self.update(entity_type, where_dict, update_dict)
