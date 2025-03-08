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

    if col_name != att_model['name']:
        raise MalformedSqliteDBError(f"Error: column {index} in table {table_name} with \
            name {col_name} does not match designated name {att_model['name']}.")
    if col_type != att_model['sqlite_type']:
        raise MalformedSqliteDBError(f"Error: column {index} in table {table_name} with \
            name {col_name} and type {col_type }does not match designated type {att_model['sqlite_type']}.")


"""
    A class to hold all methods used to access the database.
"""
class SqliteDB:
    def __init__(self, path, entity_models):
        self.path = path

        self.conversions = {
            "json_load": json.loads,
            "json_dump": json.dumps
        }

        self.get_conversion = lambda a: (self.conversions[a] if a in self.conversions else (lambda b: b))

        if utils.check_file_exists(self.path):
            self.check_existing_db(entity_models)
        else:
            self.create(entity_models)

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

        att_models = sorted(att_models, key=lambda a: a['sqlite_order'])

        for att_model in att_models:
            self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {att_model['name']} {att_model['sqlite_type']}")

        self.conn.commit()

    @_with_db
    def check_existing_db(self, entity_models):
        for entity_model in entity_models.values():
            self.cursor.execute(f"PRAGMA table_info({entity_model['table_name']})")

            columns = self.cursor.fetchall()
            num_cols = len(columns)

            base_att_models = sorted(entity_model['attributes']['base'], key=lambda a: a['sqlite_order'])
            num_base_atts = len(base_att_models)
            generated_att_models = sorted(entity_model['attributes']['generated'], key=lambda a: a['sqlite_order'])
            num_generated_atts = len(generated_att_models)
            num_table_atts = num_base_atts + num_generated_atts

            if num_cols < num_base_atts and num_cols >= num_table_atts:
                raise MalformedSqliteDBError(f"Error: table {entity_model['table_name']} in existing sqlite database has improper number of columns.")

            for base_att_index in range(num_base_atts):
                column = columns[base_att_index]
                att_model = base_att_models[base_att_index]
                check_column(base_att_index, column, att_model, entity_model['table_name'])

            gen_att_index = 0
            while num_base_atts + gen_att_index < num_cols:
                column = columns[num_base_atts + gen_att_index]
                att_model = generated_att_models[gen_att_index]
                check_column(num_base_atts + gen_att_index, column, att_model, entity_model['table_name'])
                gen_att_index += 1

            remaining_gen_atts = generated_att_models[gen_att_index:]

            self.add_cols(entity_model['table_name'], remaining_gen_atts)

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
        att_dict_list = []
        for row in zipped_results:
            att_dict = {}
            for att_model, val in row:
                att_dict[att_model['name']] = self.get_conversion(att_model['conversions']['load'])(val)
            att_dict_list.append(att_dict)
        
        return att_dict_list
    
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
        if len(update_dict.keys()) == 0:
            return

        all_atts = sorted(entity_model['attributes']['base'] + entity_model['attributes']['generated'], key=lambda a: a['sqlite_order'])
        updating_atts = [att for att in all_atts if att['name'] in update_dict]
        for att in updating_atts:
            update_dict[att['name']] = self.get_conversion(att['conversions']['store'])(update_dict[att['name']])

        update_str = ", ".join([f"{att} = ?" for att in list(update_dict.keys())])
        where_str = ", ".join([f"{att} = ?" for att in list(where_dict.keys())])
        
        update_query = f"""
            UPDATE {entity_model['table_name']}
            SET {update_str}
            WHERE {where_str}
        """

        self.cursor.execute(update_query, (list(update_dict.values()) + list(where_dict.values())))

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
