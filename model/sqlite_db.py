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
    def __init__(self, path):
        self.path = path

        self.conversions = {
            "json_load": json.loads,
            "json_dump": json.dumps
        }

        self.get_conversion = lambda a: (self.conversions[a] if a in self.conversions else (lambda b: b))

    def _with_db(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with sqlite3.connect(self.path) as conn:
                self.conn = conn
                self.cursor = conn.cursor()
                return func(self, *args, **kwargs)
        return wrapper

    """
        Create the sqlite database and the needed tables at the specified path.
    """
    @_with_db
    def create(self, entity_models):
        for entity_model in entity_models.values():
            atts = sorted(entity_model['attributes']['base'] + entity_model['attributes']['generated'], key=lambda a: a['sqlite_order'])
            create_table_query = f"CREATE TABLE {entity_model['table_name']} (" + "\n"
            att_strs = [
                f"{att['name']} {att['sqlite_type']} {'PRIMARY KEY' if entity_model['id_att'] == att['name'] else ''}"
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
    def select(self, entity_model, where_dict):
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])

        select_query = f"""
            SELECT * FROM {entity_model['table_name']} WHERE {where_str}
        """

        self.cursor.execute(select_query, tuple(where_dict.values()))

        row_tuples = self.cursor.fetchall()

        atts = sorted(entity_model['attributes']['base'] + entity_model['attributes']['generated'], key=lambda a: a['sqlite_order'])
        zipped_results = [list(zip(atts, list(row_tuple))) for row_tuple in row_tuples]
        converted_results = [[(att['name'], self.get_conversion(att['conversions']['load'])(val)) for att, val in r] for r in zipped_results]
        
        return converted_results
    
    """
        Insert some items to a given entity's table, given a list of attribute dicts
    """
    @_with_db
    def insert(self, entity_model, att_dict_list, ignore_dups=False):

        atts = sorted(entity_model['attributes']['base'] + entity_model['attributes']['generated'], key=lambda a: a['sqlite_order'])

        converted_att_lists = [
            [self.get_conversion(att['conversions']['store'])(att_dict[att["name"]]) for att in atts]
            for att_dict in att_dict_list]
        
        tuples_to_insert = [tuple(att_list) for att_list in converted_att_lists]

        insertion_query = f"""
            INSERT {'OR IGNORE' if ignore_dups else ''} 
            INTO {entity_model["table_name"]} 
            ({', '.join([att['name'] for att in atts])})
            VALUES ({', '.join(['?' for att in atts])})
        """

        self.cursor.executemany(insertion_query, tuples_to_insert)

        self.conn.commit()

    """
        Run an update query on an item in a given entity's table, given an update dict and a where dict 
    """
    @_with_db
    def update(self, entity_model, where_dict, update_dict):
        update_str = ", ".join([f"{att} = ?" for att in list(update_dict.keys())])
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])
        
        update_query = f"""
            UPDATE {entity_model['table_name']}
            SET {update_str}
            WHERE {where_str}
        """

        self.cursor.execute(update_query, tuple(update_dict.values(), where_dict.values()))

        self.conn.commit()

    """
        Run a delete query on a given entity's table
    """
    @_with_db
    def delete(self, entity_model, where_dict):
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])

        delete_query = f"""
            DELETE FROM {entity_model['table_name']} WHERE {where_str}
        """

        self.cursor.execute(delete_query, tuple(where_dict.values()))

        self.conn.commit()

    """
        Get a row for a given entity with a given id.
    """
    def get_by_id(self, entity_model, id_val):
        id_att = entity_model['id_att']

        where_dict = {id_att: id_val}

        result = self.select(entity_model, where_dict)

        if len(result) == 0:
            raise UniqueDBItemNotFound(f"Entity with id {id_val} could not be found in the sqlite database.")
        if len(result) > 1:
            raise MultipleUniqueItemsFound(f"Entity with id {id_val} had multiple results found. this should never happen but just in case")

        return result[0]

    """
        Remove a list of entities from a given entity's table, given a list of ids
    """
    def delete_by_id_list(self, entity_model, id_list):
        id_att = entity_model['id_att']

        for id_val in id_list:
            where_dict = {id_att: id_val}
            self.delete(entity_model, where_dict)

    """
        Update a list of entities given an update dict and an id
    """
    def update_by_id(self, entity_model, id_val, update_dict):
        id_att = entity_model['id_att']

        where_dict = {id_att: id_val}
        self.update(entity_model, where_dict, update_dict)
