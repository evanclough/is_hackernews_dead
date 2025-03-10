"""
    Classes for entities.
"""

import utils
from jinja2 import Template
from sqlite_db import UniqueDBItemNotFound
from chroma_db import EmbeddingsNotFoundError
import numpy as np

class LoaderError(Exception):
    def __init__(self, message):
        super().__init__(message)


class AttClassLoader:
    def __init__(self, att_class, embeddings=False):
        self.embeddings = embeddings
        self.att_class = att_class


    def load(self, entity):
        if self.embeddings:
            entity.load_from_chroma(self.att_class)

class SqliteLoader(AttClassLoader):
    def load(self, entity):
        super().load(entity)
        entity.load_from_sqlite(self.att_class)

class DictLoader(AttClassLoader):
    def __init__(self, att_class, att_dict, embeddings=False):
        super().__init__(att_class, embeddings=embeddings)
        self.att_dict = att_dict

    def load(self, entity):
        entity.load_from_att_dict(self.att_class, self.att_dict)
        super().load(entity)

class DerivedLoader(AttClassLoader):
    def __init__(self, embeddings=False):
        self.att_params = {}
        self.embedding_params={}
        super().__init__("derived", embeddings=embeddings)

    def load(self, entity):
        entity.load_derived_atts(**self.att_params)
        if self.embeddings:
            entity.load_derived_embeddings(**self.embedding_params)

class MergedLoader(AttClassLoader):
    def __init__(self, mergee=None, embeddings=False):
        super().__init__("merged", embeddings=embeddings)
        self.mergee = mergee

    def load(self, entity):
        entity.load_merged(self.mergee)
        super().load(entity)

class EntityLoader:
    def __init__(self, base=None, derived=None, generated=None, merged=None):
        self.base = base
        self.derived = derived
        self.generated = generated
        self.merged = merged

    def set_base(self, base):
        self.base = base
    def set_derived(self, derived):
        self.derived = derived
    def set_generated(self, generated):
        self.generated = generated
    def set_merged(self, merged):
        self.merged = merged

    def load(self, entity):
        att_classes = [self.base, self.derived, self.generated, self.merged]
        for att_class in att_classes:
            if att_class != None:
                att_class.load(entity)


class Entity:

    def __init__(self, entity_model, id_val, loader, sqlite, chroma, verbose=False):
        self.entity_model = entity_model
        self.id = id_val

        self.sqlite = sqlite
        self.chroma = chroma

        self.verbose = verbose

        self.atts = {}
        self.embeddings = {}

        for att_list in self.entity_model['attributes'].values():
            for att in att_list:
                if att['embed']:
                    self.embeddings[att['name']] = None 
                self.atts[att["name"]] = None
        
        self._print(f"Initialzing {self}...")

        loader.load(self)

        self._print(f"Successfully initialized {self}.")

    def get_id(self):
        return self.id

    def load_from_att_dict(self, att_class, att_dict):
        self._print(f"Manually populating base attributes from given dict for {self}...")
        for att in self.entity_model['attributes'][att_class]:
            if att['name'] in att_dict:
                self.atts[att['name']] = att_dict[att['name']]
            else:
                raise LoaderError(f"Error: in attempt to load {self} from att dict, {att_class} attribute {att['name']} was not supplied.")
    
        self._print(f"Successfully populated base attributes from given dict for {self}.")

    def load_from_sqlite(self, att_class):
        self._print(f"Loading attributes from sqlite for {self}...")
        sqlite_result = self.sqlite.get_by_id(self.entity_model, self.id)

        for att in self.entity_model['attributes'][att_class]:
            if att['name'] in sqlite_result:
                self.atts[att['name']] = sqlite_result[att['name']]
            else:
                raise LoaderError(f"Error: In loading {att_class} attributes for {self} from sqlite, {att['name']} was not present in retrieved sqlite row.")

        self._print(f"Successfully loaded attributes from sqlite for {self}.")

    def merge_text(self, mergee, att_model):
        if mergee == None:
            root_template = Template(att_model['root_template'])
            result = root_template.render(**self.atts)
        else:
            merge_template = Template(att_model['merge_template'])
            mergee_atts = {"mergee_" + key: value for key, value in mergee.get_att_dict().items()}
            my_atts = {"my_" + key: value for key, value in self.get_att_dict().items()}
            result = merge_template.render(**my_atts, **mergee_atts)

        return result

    def merge_list(self, mergee, att_model):
        if mergee == None:
            result = [self.atts[att_model['att']]]
        else:
            result = [*mergee.get_att(att_model['name']), self.atts[att_model['att']]]

        return result

    def load_merged(self, mergee):
        merge_functions = {
            "text": self.merge_text,
            "list": self.merge_list
        }

        for att_model in self.entity_model['attributes']['merged']:
            self.atts[att_model['name']] = merge_functions[att_model['merge_function']](mergee, att_model)

    def pupdate_in_sqlite(self):
        try:
            self._print(f"Updating {self} in sqlite...")
            current_sqlite_row = self.sqlite.get_by_id(self.entity_model, self.id)
            sqlite_atts = self.entity_model['attributes']['base'] + self.entity_model['attributes']['generated']

            update_dict = {}

            for att_name, sqlite_val in current_sqlite_row.items():
                if self.atts[att_name] != sqlite_val:
                    self._print(f"Updating {att_name} from {sqlite_val} to {self.atts[att_name]}")
                    update_dict[att_name] = self.atts[att_name]

            self.sqlite.update_by_id(self.entity_model, self.id, update_dict)

            self._print(f"Successfully updated {self} in sqlite.")
        except UniqueDBItemNotFound as e:
            self._print(f"Inserting {self} into sqlite...")
            self.sqlite.insert(self.entity_model, [self.atts])
            self._print(f"Successfully inserted {self} into sqlite.")

    def delete_from_sqlite(self):
        self._print(f"Deleting {self} from sqlite...")

        self.sqlite.delete_by_id_list(self.entity_model, [self.id])

        self._print(f"Successfully deleted {self} from sqlite.")

    def load_from_chroma(self, att_class):
        for att_model in self.entity_model['attributes'][att_class]:
            if att_model['embed']:
                embeddings = self.chroma.retrieve(self.entity_model, att_model, self.id)
                self.embeddings[att_model['name']] = embeddings['embeddings']

        self._print(f"Successfully loaded embeddings from chroma for {self}.")

    def delete_from_chroma(self):
        self._print(f"Deleting {self} from chroma... ")

        for att_class in self.entity_model['attributes'].values():
            for att_model in att_class:
                if att_model['embed']:
                    self.chroma.delete(self.entity_model, att_model, [self.id])

        self._print(f"Successfully deleted {self} from chroma.")

    def pupdate_in_chroma(self):
        self._print(f"Generating/updating embeddings for {self} and storing in chroma...")
        for att_class in self.entity_model['attributes'].values():
            for att_model in att_class:
                if att_model['embed'] and self.atts[att_model['name']] != None:
                    try:
                        current_embedded_val = self.chroma.retrieve(self.entity_model, att_model, self.id)['value']
                        if self.atts[att_model['name']] != current_embedded_val:
                            self._print(f"Updating embeddings for {att_model['name']}...")
                            self.chroma.update(self.entity_model, att_model, [self.id], [self.atts[att_model['name']]])
                    except EmbeddingsNotFoundError as e:
                        self.chroma.generate(self.entity_model, att_model, [self.id], [self.atts[att_model['name']]])
        self._print(f"Successfully generated/updated embeddings for {self} and stored in chroma.")

    def generate_attribute(self, att, llm, additional_context={}):
        att_model = [gen_att for gen_att in self.entity_model['attributes']['generated'] if gen_att['name'] == att]

        if len(att_model) == 0:
            raise KeyError(f"Error: attempted to generate attribute {att} for {self}, but it is not a specified generated attribute.")

        att_model = att_model[0]

        prompt_template = Template(att_model['prompt_template'])
        prompt = prompt_template.render(**self.atts, **additional_context)

        result = llm.complete(prompt)

        self.set_att(att, result)

    def get_numpy_array(self):
        result = np.array([])
        for att_class in self.entity_model['attributes'].values():
            for att_model in att_class:
                if att_model['include_when']:
                    val = self.embeddings[att_model['name']] if att_model['embed'] else np.array([self.atts[att_model['name']]])
                    print(att_model['name'], val)
                    result = np.concatenate((result, val))

        return result
        

    def set_verbose(self, verbose):
        self.verbose = verbose
    
    def _print(self, s):
        if self.verbose:
            print(s)

    def __str__(self):
        return f"Entity with id {self.id}"

    def get_id(self):
        return self.id

    def get_att(self, att):
        if att in self.atts:
            return self.atts[att]
        else:
            raise KeyError(f"Attempted to retrieve non-existant attribute {att} from {self}")


    def get_embeddings(self, att):
        if att in self.embeddings:
            return self.embeddings[att]
        else:
            raise KeyError(f"Attempted to retrieve non-existant attribute {att} from {self}")
    
    def set_att(self, att, value):
        if att in self.atts:
            #TODO: check type
            self.atts[att] = value
        else:
            raise KeyError(f"Attempted to set non-existant attribute {att} to value {value} in {self}")

    def get_att_dict(self):
        return self.atts


    def check(self, check_dict):
        
        self._print(f"{self} passes check.")
        return True



class User(Entity):
    def foo():
        return

class Submission(Entity): 
    def foo():
        return

class Root(Submission): 
    def foo():
        return

class Branch(Submission):
    def foo():
        return
