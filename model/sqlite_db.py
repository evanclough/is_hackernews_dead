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

class MalformedSqliteDBError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

def check_column(index, column, att_model, table_name):
    col_name = column[1]
    col_type = column[2]

    if col_name != att_model.name:
        raise MalformedSqliteDBError(f"Error: column {index} in table {table_name} with \
            name {col_name} does not match designated name {att_model.name}.")
    if col_type != att_model.sqlite_type:
        raise MalformedSqliteDBError(f"Error: column {index} in table {table_name} with \
            name {col_name} and type {col_type}does not match designated type {att_model.sqlite_type}.")


"""
    A class to hold all methods used to access the database.
"""
class SqliteDB:
    def __init__(self, path, forum):
        self.path = path

        if utils.check_file_exists(self.path):
            self.check_existing_db(forum)
        else:
            self.create(forum)

    def _with_db(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with sqlite3.connect(self.path) as conn:
                self.conn = conn
                self.cursor = conn.cursor()
                return func(self, *args, **kwargs)
        return wrapper

    @_with_db
    def add_cols(self, table_name, att_models):

        for att_model in att_models:
            self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {att_model.name} {att_model.sqlite_type}")

        self.conn.commit()

    @_with_db
    def check_existing_db(self, forum):
        for entity_model in forum.get_entity_models():
            self.cursor.execute(f"PRAGMA table_info({entity_model.table_name})")

            columns = self.cursor.fetchall()
            num_cols = len(columns)

            num_base_atts = len(entity_model.base.att_list)
            num_generated_atts = len(entity_model.generated.att_list)
            num_table_atts = num_base_atts + num_generated_atts

            if num_cols < num_base_atts and num_cols >= num_table_atts:
                raise MalformedSqliteDBError(f"Error: table {entity_model['table_name']} in existing sqlite database has improper number of columns.")

            for base_att_index in range(num_base_atts):
                column = columns[base_att_index]
                att_model = entity_model.base.att_list[base_att_index]
                check_column(base_att_index, column, att_model, entity_model.table_name)

            gen_att_index = 0
            while num_base_atts + gen_att_index < num_cols:
                column = columns[num_base_atts + gen_att_index]
                att_model = entity_model.generated.att_list[gen_att_index]
                check_column(num_base_atts + gen_att_index, column, att_model, entity_model.table_name)
                gen_att_index += 1

            remaining_gen_atts = entity_model.generated.att_list[gen_att_index:]

            self.add_cols(entity_model.table_name, remaining_gen_atts)

    """
        Create the sqlite database and the needed tables at the specified path.
    """
    @_with_db
    def create(self, forum):
        for entity_model in forum.get_entity_models():
            atts = entity_model.base.att_list + entity_model.generated.att_list

            create_table_query = f"CREATE TABLE {entity_model.table_name} (" + "\n"

            att_strs = [
                f"{att.name} {att.sqlite_type} {'PRIMARY KEY' if entity_model.id_att == att.name else ''}"
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
    def select(self, table_name, att_model_list, where_dict):
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])

        select_query = f"""
            SELECT * FROM {table_name} WHERE {where_str}
        """

        self.cursor.execute(select_query, tuple(where_dict.values()))

        row_tuples = self.cursor.fetchall()

        att_dict_list = []
        for row_tuple in row_tuples:
            att_dict = {}
            for att, val in list(zip(att_model_list, list(row_tuple))):
                att_dict[att.name] = val
        
        return att_dict_list
    
    """
        Insert some items to a given entity's table, given a list of attribute dicts
    """
    @_with_db
    def insert(self, table_name, att_dict_list, att_model_list, ignore_dups=False):

        tuples_to_insert = [tuple([att_dict[att_model.name] for att_model in att_model_list]) for att_dict in att_dict_list]
        
        insertion_query = f"""
            INSERT {'OR IGNORE' if ignore_dups else ''} 
            INTO {table_name} 
            ({', '.join([att.name for att in att_model_list])})
            VALUES ({', '.join(['?' for att in att_model_list])})
        """

        self.cursor.executemany(insertion_query, tuples_to_insert)

        self.conn.commit()

    """
        Run an update query on an item in a given entity's table, given an update dict and a where dict 
    """
    @_with_db
    def update(self, table_name, where_dict, update_dict):
        if len(update_dict.keys()) == 0:
            return

        update_str = ", ".join([f"{att} = ?" for att in list(update_dict.keys())])
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])
        
        update_query = f"""
            UPDATE {table_name}
            SET {update_str}
            WHERE {where_str}
        """

        self.cursor.execute(update_query, (list(update_dict.values()) + list(where_dict.values())))

        self.conn.commit()

    """
        Run a delete query on a given entity's table
    """
    @_with_db
    def delete(self, table_name, where_dict):
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])

        delete_query = f"""
            DELETE FROM {table_name} WHERE {where_str}
        """

        self.cursor.execute(delete_query, tuple(where_dict.values()))

        self.conn.commit()

    """
        Get a row for a given entity with a given id.
    """
    def get_by_id(self, id_att, table_name, id_val):
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
    def delete_by_id(self, id_att, table_name, id_val):
        id_att = entity_model['id_att']

        where_dict = {id_att: id_val}
        self.delete(table_name, where_dict)

    """
        Update a list of entities given an update dict and an id
    """
    def update_by_id(self, id_att, table_name, id_val, update_dict):
        where_dict = {id_att: id_val}
        self.update(table_name, where_dict, update_dict)
