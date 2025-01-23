"""
    A class to hold the potential response and tree classes,
    used in the dataset to hold all potential response items.
"""

import json
import functools

import classes

class PotentialResponseTree:
    def __init__(self, prt_dict, is_root=False):
        self.id = prt_dict["id"]
        self.is_root = is_root
        self.active = False

        self.kids = [PotentialResponseTree(kid_prt_dict) for kid_prt_dict in prt_dict["kids"]]

    def __str__(self):
        num_descendants = len(self.get_flattened_descendants()) - 1

        contents = f"""
        PRT {self.id}
            is {'' if self.is_root else 'not'} root
            is {'' if self.active else 'not'} active
            has {num_descendants} descendants
        """
        return contents

    def print_kids(self):
        contents = f"Kids of PRT {self.id}:\n"
        for kid in self.kids:
            contents += kid.get_id() + "\n"
        return contents

    def activate(self):
        self.active = True
    
    def deactivate(self):
        self.active = False

    def is_active(self):
        return self.active

    def get_id(self):
        return self.id

    def get_is_root(self):
        return self.is_root
    
    def get_kids(self):
        return self.kids

    def set_kids(self, new_kids):
        self.kids = new_kids

    """
        Check if an item of a given id is present in this tree
    """
    def check_contains_item(self, item_id):
        f = lambda n: n["me"].get_id() == item_id or n["kids"]
        reduce_kids_f = lambda acc, n: n or acc
        reduce_kids_acc = False
        return self.dfs(f, reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc)

    """
        Get a member item of this tree, given its id.
        If not present, return None.
    """
    def get_item(self, item_id):
        if self.check_contains_item(item_id):
            f = lambda n: n["me"] if n["me"].get_id() == item_id else n["kids"]
            reduce_kids_f = lambda acc, n: n if n != None else acc
            reduce_kids_acc = None
            return self.dfs(f, reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc)
        else:
            return None

    """
        Get the parent of a given id in this tree.
        If not present, return None.
    """
    def get_parent_of_item(self, child_id):
        if self.check_contains_item(child_id):
            f = lambda n: n["me"] if (child_id in [kid.get_id() for kid in n["me"].get_kids()]) else n["kids"]
            reduce_kids_f = lambda acc, n: n if n != None else acc
            reduce_kids_acc = None
            return self.dfs(f, reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc)
        else:
            return None
    
    """
        Get a flattened list of this node and all of its descendants.
    """
    def get_flattened_descendants(self):
        return self.dfs(lambda c: [c["me"], *c["kids"]], reduce_kids_f=lambda acc, c: [*acc, *c], reduce_kids_acc=[])

    """
        Get the full branch of an item in this potential response tree, given its id.
        If not present, return None.
    """
    def get_branch(self, item_id):
        f = lambda n: [n["me"]] if n["me"].get_id() == item_id else ([n["me"], *n["kids"]] if n["kids"] != None else None)
        reduce_kids_f = lambda acc, n: (n if n != None else acc)
        reduce_kids_acc = None
        return self.dfs(f, reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc)

    """
        Remove an item and all of its descendants this potential response tree, given an ID.
        If not present, or the ID is the root, return None.
    """
    def remove_item_and_descendants(self, item_id):
        if self.check_contains_item(item_id) or self.get_id() == item_id:
            parent = self.get_parent_of_item(item_id)
            new_kids = [kid for kid in parent.get_kids() if kid.get_id() != item_id]
            parent.set_kids(new_kids)
        else:
            return None

    """
        Add a child to some arbitrary parent in this PRT's descendants, given both ids.
    """
    def add_kid_to_descendant(self, child_id, parent_id):
        parent = self.get_item(parent_id)
        kid = PotentialResponseTree({"id": child_id, "kids": []})
        new_kids = [*parent["self"].kids, kid]
        parent.set_kids(new_kids)

    """
        Add a child to this branch, given an existing 
    """
    def add_kid(self, child_id):
        kid = PotentialResponseTree({"id": child_id, "kids": []})
        new_kids = [*self.get_kids(), kid]
        self.set_kids(new_kids)

    """
        Fetch the full contents of this leaf with data from given sources.
    """
    def fetch_contents(self, sqlite_db=None, chroma_db=None):
        if self.is_root:
            contents = classes.Post(self.id, sqlite_db=sqlite_db, chroma_db=chroma_db)
        else:
            contents = classes.Comment(self.id, sqlite_db=sqlite_db, chroma_db=chroma_db)

        return contents
        

    """
        Check all items in this tree
        to see whether all of the data necessary to 
        generate a full feature set with it is present, and 
        if not, remove it, and all of its descendants.
    """
    def clean(self, sqlite_db):
        try:
            contents = self.fetch_contents(sqlite_db=sqlite_db)
            if contents.check(sqlite_db):
                clean_kids = [kid for kid in self.kids if kid.clean(sqlite_db)]
                self.kids = clean_kids
                return True
            else:
                return False
        except Exception as e:
            print(f"Error in potential response item:")
            print(e)
            print("Removing.\n")
            return False

    """
        Convert back to the original dict form.
    """
    def convert_to_dict(self):
        return self.dfs(lambda c: {"id": c["me"].get_id(), "kids": c["kids"]}, reduce_kids_f=lambda acc, c: [*acc, c], reduce_kids_acc=[])

    """
        Iterate through this potential response tree via a DFS.
        Many options provided.
    """
    def dfs(self, f, sqlite_db=None, filter_f=None, reduce_kids_f=None, reduce_kids_acc=None, depth=0):

        f_inp = {
            "me": self,
            "contents": None,
            "kids": None,
            "depth": depth
        }

        if sqlite_db != None:
            f_inp["contents"] = self.fetch_contents(sqlite_db=sqlite_db)

        if filter_f != None:
            filter_res = filter_f(f_inp)
            if filter_res == False:
                return None

        kid_results = [kid.dfs(f, sqlite_db=sqlite_db, filter_f=filter_f, reduce_kids_f=reduce_kids_f,reduce_kids_acc=reduce_kids_acc, depth=depth+1) for kid in self.kids] 

        if reduce_kids_f != None:
            reduced = functools.reduce(reduce_kids_f, kid_results, reduce_kids_acc)
            f_inp["kids"] = reduced

        return f(f_inp)

    """
        Recursively activate all children prior to a given time.
    """
    def activate_before_time(self, sqlite_db, time):

        filter_f = lambda c: c["contents"].time < time if c["contents"] != None else False
        activate = lambda c: c["me"].activate()
        self.dfs(activate, sqlite_db=sqlite_db, filter_f=filter_f)

    """
        Recursively retrieve a list of all active branches in this potential response tree
    """
    def get_all_active_branches(self):
        
        filter_f = lambda c: c["me"].is_active()

        reduce_kids_f = lambda acc, c: acc if c == None else [*acc, *c]

        reduce_kids_acc = []

        f = lambda c: [*[[c["me"]] + kid for kid in c["kids"]], [c["me"]]]
        
        return self.dfs(f, filter_f=filter_f, reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc)


"""
    An exception class for all PRF related errors.
"""
class PotentialResponseForestError(Exception):
    def __init__(self, message):
        super().__init__(message)

"""
    A class to hold all of the potential response trees present in the dataset.
"""

class PotentialResponseForest:
    def __init__(self, name, prf):
        self.name = name
        self.roots = [PotentialResponseTree(prt, is_root=True) for prt in prf]
    
    def get_roots(self):
        return self.roots

    def set_roots(self, new_roots):
        self.roots = new_roots

    """
        Get the current potential response forest in the original list format.
    """
    def get_current_prf(self):
        current_prf = [root.convert_to_dict() for root in self.roots]
        return current_prf

    """
        Check whether or not a potential response item of a given id is present in the list.
        If there are multiple present, raise an error.
    """
    def check_contains_item(self, item_id):
        filtered_roots = [root for root in self.roots if root.check_contains_item(item_id)]
        if len(filtered_roots) == 1:
            return True
        elif len(filtered_roots) == 0:
            return False
        else:
            raise PotentialResponseForestError(f"Error: item with id {item_id} is present in multiple potential response trees, with roots {[root.get_id() for root in filtered_roots]}")

    """
        Get an item's root if it exists among member trees, otherwise, raise an error.
    """
    def get_root_of_item(self, item_id):
        if self.check_contains_item(item_id):
            root = [root for root in self.roots if root.check_contains_item(item_id)][0]
            return root
        else:
            raise PotentialResponseForestError(f"Error: Attempt to get root of item of id {item_id} not present in forest")
    
    """
        Get an item's node if it exists among member trees, otherwise, raise an error.
    """
    def get_item(self, item_id):
        if self.check_contains_item(item_id):
            root_of_item = self.get_root_of_item(item_id)
            item = root_of_item.get_item(item_id)
            return item
        else:
            raise PotentialResponseForestError(f"Error: Attempt to get item of id {item_id} not present in forest.")

    """
        Get a list of items.
    """
    def get_items(self, item_ids):
        items = [self.get_item(item_id) for item_id in item_ids]
        return items

    """
        Get the full branch of an item, given its id.
        If not present, raise an error.
    """
    def get_branch(self, item_id):
        if self.check_contains_item(item_id):
            root_of_item = self.get_root_of_item(item_id)
            branch = root_of_item.get_branch(item_id)
            return branch
        else:
            raise PotentialResponseForestError(f"Error: Attempt to get branch of id {item_id} not present in forest.")


    """
        Remove an item of a given id's branch  in one of the trees
        If it's not found, raise an error
    """
    def remove_item(self, item_id):
        if self.check_contains_item(item_id):
            root_of_item = self.get_root_of_item(item_id)
            if root_of_item.get_id() == item_id:
                self.remove_root(item_id)
            else:
                root_of_item.remove_item_and_descendants(item_id)
        else:
            raise PotentialResponseForestError(f"Error: Attempt to remove item of id {item_id} not present in forest.")

    """
        Remove a list of items, by their ids.
        Handle the not found error if thrown as if this is done in batches,
        parent comments may be removed first and later children may not be found, which is fine
    """
    def remove_items(self, item_ids):
        for item_id in item_ids:
            try:
                self.remove_item(item_id)
            except PotentialResponseForestError as e:
                print(f"Item with id {item_id} has already been removed. Continuing.")
                continue

    """
        Add a root to the forest, given its ID.
    """
    def add_root(self, root_id):
        new_root = PotentialResponseTree({"id": root_id, "kids": []}, is_root=True)
        new_roots = [*self.roots, new_root]
        self.set_roots(new_roots)

    """
        Add a list of new roots to the forest, given their ids
    """
    def add_roots(self, root_ids):
        for root_id in root_ids:
            self.add_root(root_id)

    """
        Remove a root from the forest, given its ID.
    """
    def remove_root(self, root_id):
        new_roots = [root for root in self.roots if root.get_id() != root_id]
        self.set_roots(new_roots)

    """
        Remove a root by their ids.
    """
    def remove_roots(self, root_ids):
        for root_id in root_ids:
            self.remove_root(root_id)

    """
        Activate all potential response nodes made prior to a given time.
    """
    def activate_before_time(self, sqlite_db, time):
        for root in self.roots:
            root.activate_before_time(sqlite_db, time)

    """
        Clean all roots.
    """
    def clean(self, sqlite_db):
        clean_roots = [root for root in self.roots if root.clean(sqlite_db)]
        self.roots = clean_roots

    """
        Get a list of timestamps for all roots.
    """
    def get_root_times(self, sqlite_db):
        root_times = [root.fetch_contents(sqlite_db=sqlite_db).time for root in self.roots]
        return root_times

    """
        Get all active branches contained in the forest.
    """
    def get_all_active_branches(self, sqlite_db=None):
        all_active_branches = functools.reduce(lambda acc, b: [*acc, *b], [root.get_all_active_branches(sqlite_db=sqlite_db) for root in self.roots], [])
        return all_active_branches