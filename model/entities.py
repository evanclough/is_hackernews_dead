"""
    Classes for entities.
"""

import utils
from sqlite_db import UniqueDBItemNotFound
from chroma_db import EmbeddingsNotFoundError

class LoaderError(Exception):
    def __init__(self, message):
        super().__init__(message)


class AttClassLoader:
    def __init__(self, name, embeddings=False):
        self.embeddings = embeddings
        self.needs_chroma = embeddings
        self.needs_sqlite = False
        self.name = name

    def check_sources(self):
        return True

class BaseLoader(AttClassLoader):
    def __init__(self, from_sqlite=False, from_att_dict=False, att_dict=None, **kwargs):
        if from_sqlite and from_att_dict:
            raise LoaderError(f"Error: cannot load in base attributes from both sqlite and an att dict.")

        self.from_sqlite = from_sqlite
        self.needs_sqlite = from_sqlite

        self.from_att_dict = from_att_dict
        self.att_dict = att_dict

        super().__init__("base", **kwargs)

    def check_sources(self):
        if self.from_att_dict and self.att_dict == None:
            raise LoaderError(f"Error: loader requires att dict, but att dict was not supplied.")

class DerivedLoader(AttClassLoader):
    def __init__(self, **kwargs):
        self.needs_sqlite = True
        self.params = {}
        super().__init__("derived", **kwargs)

class EntityLoader:
    def __init__(self, base=None, derived=None):
        self.sqlite = None
        self.chroma = None
        self.needs_sqlite = False
        self.needs_chroma = False

        self.base = base
        self.derived = derived
        self.att_classes = [self.base, self.derived]

        for att_class in self.att_classes:
            if att_class != None:
                self.needs_sqlite = self.needs_sqlite or att_class.needs_sqlite
                self.needs_chroma = self.needs_chroma or att_class.needs_chroma

    def check_sources(self):
        for att_class in self.att_classes:
            if att_class != None:
                att_class.check_sources()
        if self.needs_chroma and self.chroma == None:
            raise LoaderError(f"Error: loader requires chroma, but chroma object was not populated.")
        if self.needs_sqlite and self.sqlite == None:
            raise LoaderError(f"Error: loader requires sqlite, but sqlite object was not populated.")



class Entity:

    def __init__(self, entity_model, id_val, loader, verbose=False):
        self.entity_model = entity_model
        self.id = id_val
        
        self.status = {
            "base": {
                "values": False,
                "embeddings": False,
                "checker": self.check_base_atts
            },
            "derived": {
                "values": False,
                "embeddings": False,
                "checker": self.check_derived_atts
            }
        }

        self.verbose = verbose

        self.atts = {}
        self.embeddings = {}

        for att_list in self.entity_model['attributes'].values():
            for att in att_list:
                if att['embed']:
                    self.embeddings[att['name']] = None 
                self.atts[att["name"]] = None
        
        
        self._print(f"Initialzing {self}...")

        loader.check_sources()

        if loader.base != None:
            if loader.base.from_sqlite:
                self._load_from_sqlite('base', loader.sqlite)
                self.status['base']['values'] = True
            if loader.base.from_att_dict:
                self._load_from_att_dict('base', loader.base.att_dict)
                self.status['base']['values'] = True

        if loader.derived != None:
            self.load_derived_atts(loader.sqlite, **loader.derived.params)
            self.status['derived']['values'] = True


        for att_class in loader.att_classes:
            if att_class != None:
                if att_class.embeddings:
                    self._load_from_chroma(att_class.name, loader.chroma)
                    self.status[att_class.name]['embeddings'] = True

        self._print(f"Successfully initialized {self}.")

    def get_id(self):
        return self.id


    def _load_from_att_dict(self, att_class, att_dict):
        self._print(f"Manually populating base attributes from given dict for {self}...")
        for att in self.entity_model['attributes'][att_class]:
            if att['name'] in att_dict:
                self.atts[att['name']] = att_dict[att['name']]
            else:
                raise LoaderError(f"Error: in attempt to load {self} from att dict, {att_class} attribute {att['name']} was not supplied.")
    
        self._print(f"Successfully populated base attributes from given dict for {self}.")


    def _load_from_sqlite(self, att_class, sqlite):
        self._print(f"Loading attributes from sqlite for {self}...")
        sqlite_result = sqlite.get_by_id(self.entity_model, self.id)

        for att in self.entity_model['attributes'][att_class]:
            if att['name'] in sqlite_result:
                self.atts[att['name']] = sqlite_result[att['name']]
            else:
                raise LoaderError(f"Error: In loading {att_class} attributes for {self} from sqlite, {att['name']} was not present in retrieved sqlite row.")

        self._print(f"Successfully loaded attributes from sqlite for {self}.")

    def pupdate_in_sqlite(self, sqlite):
        try:
            self._print(f"Updating {self} in sqlite...")
            current_sqlite_row = sqlite.get_by_id(self.entity_model, self.id)
            sqlite_atts = self.entity_model['attributes']['base'] + self.entity_model['attributes']['generated']

            update_dict = {}

            for att_name, sqlite_val in current_sqlite_row.items():
                if self.atts[att_name] != sqlite_val:
                    self._print(f"Updating {att_name} from {sqlite_val} to {self.atts[att_name]}")
                    update_dict[att_name] = self.atts[att_name]

            sqlite.update_by_id(self.entity_model, self.id, update_dict)

            self._print(f"Successfully updated {self} in sqlite.")
        except UniqueDBItemNotFound as e:
            self._print(f"Inserting {self} into sqlite...")
            sqlite.insert(self.entity_model, [self.atts])
            self._print(f"Successfully inserted {self} into sqlite.")

    def delete_from_sqlite(self, sqlite):
        self._print(f"Deleting {self} from sqlite...")

        sqlite.delete_by_id_list(self.entity_model, [self.id])

        self._print(f"Successfully deleted {self} from sqlite.")

    def _load_from_chroma(self, att_class, chroma):
        for att_model in self.entity_model['attributes'][att_class]:
            if att_model['embed']:
                if att_model['name'] in self.custom_embedding_functions:
                    self.custom_embedding_functions[att_model['name']]['load'](self, chroma)
                else:
                    embeddings = chroma.retrieve(self.entity_model, att_model, self.id)
                    self.embeddings[att_model['name']] = embeddings['embeddings']


        self._print(f"Successfully loaded embeddings from chroma for {self}.")

    def delete_from_chroma(self, chroma):
        self._print(f"Deleting {self} from chroma... ")

        for att_class in self.entity_model['attributes'].values():
            for att_model in att_class:
                if att_model['embed']:
                    if att_model['name'] in self.custom_embedding_functions:
                        self.custom_embedding_functions[att_model['name']]['delete'](self, chroma)
                    else:
                        chroma.delete(self.entity_model, att_model, [self.id])

        self._print(f"Successfully deleted {self} from chroma.")

    def pupdate_in_chroma(self, chroma):
        self._print(f"Generating embeddings for {self} and storing in chroma...")
        for att_class in self.entity_model['attributes'].values():
            for att_model in att_class:
                if att_model['embed'] and self.atts[att_model['name']] != None:
                    if att_model['name'] in self.custom_embedding_functions:
                        self.custom_embedding_functions[att_model['name']]['pupdate'](self, chroma)
                    else:
                        try:
                            current_embedded_val = chroma.retrieve(self.entity_model, att_model, self.id)['value']
                            if self.atts[att_model['name']] != current_embedded_val:
                                self._print(f"Updating embeddings for {att_model['name']}...")
                                chroma.update(self.entity_model, att_model, [self.id], [self.atts[att_model['name']]])
                        except EmbeddingsNotFoundError as e:
                            chroma.generate(self.entity_model, att_model, [self.id], [self.atts[att_model['name']]])


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

        for att_class_name, att_class in check_dict.items():
            if self.status[att_class_name]['values'] != att_class['values']:
                self._print(f"{self} fails check, as {att_class_name} attributes do not have values populated.")
                return False
            if self.status[att_class_name]['embeddings'] != att_class['embeddings']:
                self._print(f"{self} fails check, as {att_class_name} attributes do not have embeddings populated.")
                return False
            check_result = self.status[att_class_name]['checker'](**att_class['checker_params'])
            if not check_result['success']:
                self._print(f"{self} fails check, as {att_class_name} failed check method: {check_result['message']}")
                return False
        
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
