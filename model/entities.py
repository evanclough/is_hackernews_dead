"""
    Classes for entities.
"""

import utils
from jinja2 import Template
from sqlite_db import UniqueDBItemNotFound
from chroma_db import EmbeddingsNotFoundError
import numpy as np

class Entity:

    def __init__(self, id_val, sqlite, chroma, verbose=False):
        self.id = id_val
        self.sqlite = sqlite
        self.chroma = chroma
        self.verbose = verbose

        self.base = SqliteAttClassValues(self.id, self.model.base, self.sqlite, self.chroma)
        self.derived = DerivedAttClassValues(self.id, self.model.derived, self.sqlite, self.chroma)
        self.generated = GeneratedAttClassValues(self.id, self.model.generated, self.sqlite, self.chroma)

    def load_from_sqlite(self):
        sqlite_row = self.sqlite.get_by_id(self.model.id_att, self.model.table_name, self.id)
        self.base.fill_from_dict(sqlite_row)
        self.generated.fill_from_dict(sqlite_row)
    
    def derive(self):
        self.derived.derive(self.base.values, self.generated.values)
    
    def load_from_chroma(self):
        self.base.load_from_chroma()
        self.derived.load_from_chroma()
        self.generated.load_from_chroma()
    
    def load(self):
        self.load_from_sqlite()
        self.derive()
        self.load_from_chroma()

    def store_in_sqlite(self):
        try:
            self._print(f"Updating {self} in sqlite...")
            current_sqlite_row = self.sqlite.get_by_id(self.entity_model, self.id)
            self.base.update_in_sqlite()
            self.generated.update_in_sqlite()
        except UniqueDBItemNotFound as e:
            self._print(f"Inserting {self} into sqlite...")
            self.sqlite.insert(self.table_name, [{**self.base.values, **self.generated.values}], self.model.base.att_list + self.model.generated.att_list)
            self._print(f"Successfully inserted {self} into sqlite.")
    
    def store_in_chroma(self):
        self.base.pupdate_in_chroma()
        self.derived.pupdate_in_chroma()
        self.generated.pupdate_in_chroma()

    def store(self):
        self.store_in_sqlite()
        self.store_in_chroma()

    def delete_from_sqlite(self):
        self.sqlite.delete_by_id(self.model.id_att, self.model.table_name, self.id)
    
    def delete_from_chroma(self):
        self.base.delete_from_chroma()
        self.derived.delete_from_chroma()
        self.generated.delete_from_chroma()

    def delete(self):
        self.delete_from_sqlite()
        self.delete_from_chroma()

    def generate(self, llm):
        self.generated.generate(llm, self.base.values, self.derived.values)


    def set_verbose(self, verbose):
        self.verbose = verbose
    
    def _print(self, s):
        if self.verbose:
            print(s)

    def __str__(self):
        return f"Entity with id {self.id}"

    def get_id(self):
        return self.id

class User(Entity):
    def foo():
        return

class Submission(Entity): 
    def foo():
        return

class Root(Submission): 
    def foo():
        return

class Stem(Submission):
    def foo():
        return

class Forum:
    def __init__(self, user, root, stem):
        self.user = user
        self.root = root
        self.stem = stem

    def get_entity_models(self):
        return [self.user.model, self.root.model, self.stem.model]

class EntityModel:
    def __init__(self, id_att, table_name, base, derived, generated):
        self.id_att = id_att
        self.table_name = table_name
        self.base = base
        self.derived = derived
        self.generated = generated
        self.all_att_classes = [self.base, self.derived, self.generated]
        self.all_atts = [*att_class.att_list for att_class in self.att_classes]
        self.all_embedded_atts = [att for att in self.all_atts if att.store_embeddings]

        for att in self.all_att_classes:
            att.add_context(self.id_att, self.table_name)
    
class AttClassModel:
    def __init__(self, att_list):
        self.att_list = att_list
        self.embedded_list = [att for att in att_list if att.store_embeddings]
        

class AttModel:
    def __init__(self, name, store_embeddings, in_when, py_type, update_comparator=None):
        self.name = name
        self.store_embeddings = store_embeddings
        self.in_when = in_when
        self.update_comparator = update_comparator
    
    def add_context(self, id_att, table_name):
        self.id_att = id_att
        self.table_name = table_name

class SqliteAttModel(AttModel):
    def __init__(self, name, store_embeddings, in_when, py_type, sqlite_type, update_comparator=None, load_conversion=None, store_conversion=None):
        super().__init__(name, store_embeddings, in_when, py_type, update_comparator=update_comparator)
        self.sqlite_type = sqlite_type
        self.load_conversion = load_conversion
        self.store_conversion = store_conversion
    
class GeneratedAttModel(SqliteAttModel):
    def __init__(self, name, store_embeddings, in_when, py_type, sqlite_type, prompt, update_comparator=None, load_conversion=None, store_conversion=None):
        super().__init__(name, store_embeddings, in_when, py_type, sqlite_type, update_comparator=update_comparator, load_conversion=load_conversion, store_conversion=store_conversion)
        self.prompt = prompt

class DerivedAttModel(AttModel):
    def __init__(self, name, store_embeddings, in_when, py_type, derive_function, update_comparator=None):
        super().__init__(name, store_embeddings, in_when, py_type, update_comparator=update_comparator)
        self.derive_function = derive_function

class AttClassValues:
    def __init__(self, id_val, model, sqlite, chroma):
        self.id = id_val
        self.model = model
        self.sqlite = sqlite
        self.chroma = chroma
        self.values = {}
        self.embeddings = {}
        for att in self.model.att_list:
            self.values[att.name] = None
            if att.store_embeddings:
                self.embeddings[att.name] = None

    def get_value(self, att_name):
        if att_name in self.values:
            return self.values[att_name]
        else:
            raise KeyError(f"Error getting attribute {att_name}: not present in model.")

    def set_value(self, att_name, att_value):
        if att_name in self.values:
            self.values[att_name] = att_value
        else:
            raise KeyError(f"Error setting attribute {att_name} to {att_value}: not present in model.")

    def get_embeddings(self, att_name):
        if att_name in self.embeddings:
            return self.embeddings[att_name]
        else:
            raise KeyError(f"Error getting embeddings for attribute {att_name}: not designated to store embeddings.")
    
    def set_embeddings(self, att_name, embeddings):
        if att_name in self.embeddings:
            self.embeddings[att_name] = embeddings
        else:
            raise KeyError(f"Error setting embeddings of  {att_name} to {embeddings}: not designated to store embeddings.")

    def fill_from_dict(self, att_dict):
        for att in self.model.att_list:
            if att.name in att_dict:
                self.values[att.name] = att_dict[att.name]
            else:
                raise KeyError(f"Error filling values from dict: att {att.name} is not present in given dict.")

    def load_from_chroma(self):
        for att in self.model.embedded_list:
            if att.py_type == "entity":
                self.get_value(att.name).load_from_chroma()
            elif att.py_type == "list(entity)":
                for entity in self.get_value(att.name):
                    entity.load_from_chroma()
            else:
                embeddings = self.chroma.retrieve(att, self.id)['embeddings']
                self.set_embeddings(att_model.name, embeddings)

    def pupdate_in_chroma(self):
        for att in self.model.embedded_list:
            if att.py_type == "entity":
                self.get_value(att.name).store_in_chroma()
            elif att.py_type == "list(entity)":
                for entity in self.get_value(att.name):
                    entity.store_in_chroma()
            else:
                current_val = self.get_value(att.name)
                try:
                    current_chroma_val = self.chroma.retrieve(att, self.id)['value']
                    if att.update_comparator == None:
                        needs_update = current_val != current_embedded_val
                    else:
                        needs_update = att.update_comparator(current_val, current_chroma_val)
                    if needs_update:
                        self.chroma.update(att, [self.id], [current_val])
                except EmbeddingsNotFoundError as e:
                    self.chroma.generate(att, [self.id], [current_val])
        
    def delete_from_chroma(self):
        for att in self.model.embedded_list:
            if att.py_type == "entity":
                self.get_value(att.name).delete_from_chroma()
            elif att.py_type == "list(entity)":
                for entity in self.get_value(att.name):
                    entity.delete_from_chroma()
            else:
                self.chroma.delete(att, [self.id])

class SqliteAttClassValues(AttClassValues):
    def convert_load(att, value):
        if att.load_conversion == None:
            if value == None:
                return None
            if att.py_type == "str":
                return str(value)
            elif att.py_type == "int":
                return int(value)
            elif att.py_type == "dict":
                return json.loads(value)
            else:
                raise KeyError(f"Error: in loading from sqlite, attribute {att.name} has unsupported py type.")
        else:
            return att.load_conversion(value)
    
    def convert_store(att, value):
        if att.store_conversion == None:
            if value == None:
                return None
            if att.sqlite_type == "TEXT":
                if att.py_type == "dict":
                    return json.dumps(value)
                else:
                    return str(value)
            elif att.sqlite_type == "INTEGER":
                return int(value)
            else:
                raise KeyError(f"Error: in storing to sqlite, attribute {att.name} has unsupported py/sqlite types")
        else:
            return att.store_conversion(value)

    def load_from_sqlite(self):
        sqlite_result = self.sqlite.get_by_id(self.id_att, self.table_name, self.id)
        for att in self.model.att_list:
            if att.name in sqlite_result:
                self.set_value(att.name, self.convert_load(att, sqlite_result[att.name]))
            else:
                raise KeyError(f"Error: in loading attributes from sqlite, {att.name} is not present in sqlite result.")

    def update_in_sqlite(self):
        current_sqlite_row = self.sqlite.get_by_id(self.id_att, self.table_name, self.id)
        update_dict = {}
        for att in self.model.att_list:
            if att.name in current_sqlite_row:
                current_val = self.get_value(att.name)
                stored_val = self.convert_load(att, current_sqlite_row[att.name])

                if att.update_comparator == None:
                    needs_update = current_val != stored_val
                else:
                    needs_update = att.update_comparator(current_val, stored_val)
                    
                if needs_update:
                    update_dict[att.name] = current_val
            else:
                raise KeyError(f"Error: in updating attributes from sqlite, {att.name} is not present in sqlite result.")

        self.sqlite.update_by_id(self.id_att, self.table_name, self.id, update_dict)

class GeneratedAttClassValues(SqliteAttClassValues):
    def generate_attribute(self, att_name, llm, base_values, derived_values):
        prompt_template = Template(att.prompt)
        prompt = prompt_template.render(**base_values, **derived_values, **self.values)

        result = llm.complete(prompt)

        self.set_value(att_name, result)
    
    def generate(self, llm, base_values, derived_values):
        for att in self.model.att_list:
            self.generate_attribute(att.name, llm, base_values, derived_values)

class DerivedAttClassValues(AttClassValues):
    def derive_attributes(self, base_values, generated_values):
        for att in self.model.att_list:
            self.set_value(att.name, att.derive_function(base_values, self.values, generated_values))

    