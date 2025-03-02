"""
    Classes for entities.
"""

import utils

class ItemLoadError(Exception):
    def __init__(self, message):
        super().__init__(message)

class Entity:

    def __init__(self, entity_type, entity_model, id_val, load={}, verbose=False):
        self.entity_type = entity_type
        self.entity_model = entity_model
        self.id = id_val

        self.has_base_atts = False
        self.has_embeddings = False
        self.has_derived_atts = False
        
        self.verbose = verbose

        self.atts = {}
        self.embeddings = {}

        for att_list in self.entity_model['attributes'].values():
            for att in att_list:
                if att['embed']:
                    self.embeddings[att['name']] = None 
                self.atts[att["name"]] = None
        
        self._print(f"Initialzing {self}...")

        if 'base' in load:
            if 'dict' in load['base']:
                self._init_from_base_atts_dict(load['base']['dict'])
            if 'sqlite' in load['base']:
                self._load_from_sqlite(load['base']['sqlite'])

        if 'derived' in load:
            chroma = load['derived']['chroma'] if 'chroma' in load['derived'] else None
            sqlite = load['derived']['sqlite'] if 'sqlite' in load['derived'] else None
            other = load['derived']['other'] if 'other' in load['derived'] else None
            self._load_derived_atts_wrapper(sqlite=sqlite, chroma=chroma, **other)
        
        if 'embeddings' in load:
            chroma = load['embeddings']['chroma']
            self._load_from_chroma(chroma)

        self._print(f"Successfully initialized {self}.")

    def get_id(self):
        return self.id


    def _init_from_base_atts_dict(self, base_atts_dict):
        self._print(f"Manually populating base attributes from given dict for {self}...")
        for att, value in base_atts_dict.items():
            if att in self.atts:
                self.atts[att] = value
            else:
                raise ItemLoadError(f"Attempted to insert non-existant attribute {att} into {self}")
    
        self.has_base_atts = True

        self._print(f"Successfully populated base attributes from given dict for {self}.")


    def _load_from_sqlite(self, sqlite):
        self._print(f"Loading attributes from sqlite for {self}...")
        sqlite_result = sqlite.get_by_id(self.entity_model, self.id)

        for att, val in sqlite_result:
            self.atts[att] = val
        
        self.has_base_atts = True

        self._print(f"Successfully loaded attributes from sqlite for {self}.")

    def _load_derived_atts_wrapper(self, sqlite=None, chroma=None, **kwargs):
        self._print(f"Loading derived attributes for {self}...")

        self.load_derived_atts(sqlite=sqlite, chroma=chroma, **kwargs)

        self.has_derived_atts = True

        self._print(f"Successfully loaded derived attributes for {self}.")

    def _load_from_chroma(self, chroma):
        self._print(f"Loading embeddings from chroma for {self}...")

        for att_model_list in self.entity_model['attributes'].values():
            for att_model in att_model_list:
                if att_model['embed']:
                    if att_model['name'] in self.custom_embedding_functions:
                        self.custom_embedding_functions[att_model['name']]['load'](chroma)
                    else:
                        embeddings = chroma.retrieve(self.entity_model, att_model, [self.id])
                        self.embeddings[att_model['name']] = embeddings

        self.has_embeddings = True

        self._print(f"Successfully loaded embeddings from chroma for {self}.")

    def generate_embeddings(self, chroma):
        self._print(f"Generating embeddings and storing in chroma for {self}...")

        for att_model_list in self.entity_model['attributes'].values():
            for att_model in att_model_list:
                if att_model['embed']:
                    if att_model['name'] in self.custom_embedding_functions:
                        self.custom_embedding_functions[att_model['name']]['store'](chroma)
                    else:
                        chroma.generate(self.entity_model, att_model, [self.id], [self.atts[att_model['name']]])


    def set_verbose(self, verbose):
        self.verbose = verbose
    
    def _print(self, s):
        if self.verbose:
            print(s)



    def __str__(self):
        return f"{self.entity_type} with id {self.id}"

    def _long_str(self):
        contents = str(self) + "\n"
        if self.has_base_atts:
            contents += "\t" + "Base attributes: " + "\n"
            for att, value in self.atts.items():
                if att in s:
                    contents += "\t" + f"{att}: {value}" + "\n"
        else:
            contents += "\tDoes not have base attributes loaded.\n"

        if self.has_loaded_atts:
            contents += "\t" + "Loaded attributes" + "\n"
            for att, value in self.atts.items():
                contents += "\t" + f"{att}: {value}" + "\n"
        else:
            contents += "\tDoes not have loaded attributes.\n"

        contents += "\t" + f"Embeddings are {'' if self.has_embeddings else 'not'} loaded." + "\n"
        
        return contents

    def get_id(self):
        return self.id

    def get_att(self, att):
        if att in self.atts:
            return self.atts[att]
        else:
            raise KeyError(f"Attempted to retrieve non-existant attribute {att} from {self}")
    
    def set_att(self, att, value):
        if att in self.atts:
            #TODO: check type
            self.atts_dict[att] = value
        else:
            raise KeyError(f"Attempted to set non-existant attribute {att} to value {value} in {self}")

    def get_att_dict(self):
        return self.atts


    def check(self, checklist={}):
        att_type_list = [
            {
                "name": "base",
                "has_or_not": self.has_base_atts,
                "check_f": self.check_base_atts
            },
            {
                "name": "embeddings",
                "has_or_not": self.has_embeddings,
                "check_f": self.check_embeddings
            },
            {
                "name": "derived",
                "has_or_not": self.has_derived_atts,
                "check_f": self.check_derived_atts
            }
        ]

        self._print(f"Checking {self}...")

        for att_type in att_type_list:
            if att_type['name'] in checklist:
                self._print(f"Checking {att_type['name'] + (' attributes' if att_type['name'] != 'embeddings' else '')} of {self}...")
                if not att_type["has_or_not"]:
                    self._print(f"{self} fails check, as it does not have {att_type['name']} loaded.")
                    return False
                check_result = att_type['check_f'](**(checklist[att_type['name']]))
                if not check_result['success']:
                    self._print(f"{self} fails check, as its {att_type['name']} failed check: {check_result['message']}.")
                    return False
        
        self._print(f"{self} passes check.")
        return True



class User(Entity):
    def __init__(self, *args, **kwargs):

        super().__init__("user", *args, **kwargs)

class Submission(Entity): 
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

class Root(Submission): 
    def __init__(self, *args, **kwargs):

        super().__init__("root", *args, **kwargs)

class Branch(Submission):
    def __init__(self, *args, **kwargs):

        super().__init__("branch", *args, **kwargs)
