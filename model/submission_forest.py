"""
    A class to hold the potential response and tree classes,
    used in the dataset to hold all potential response items.
"""

import json
import functools

from collections import deque

import entities

class Branch:
    def __init__(self, root):
        self.root = root
        self.stems = []

    def push_stem(self, stem):
        self.stems.append(stem)

    def pop_stem(self):
        self.stems.pop()

class SubmissionTreeNode:

    
    def __init__(self, st_dict, root_factory, stem_factory, verbose=False, parent=None):
        self.id = st_dict["id"]
        self.root_factory = root_factory
        self.stem_factory = stem_factory
        self.verbose = verbose
        self.is_root = parent == None
        self.parent = parent
        self.active = False

        self.kids = [SubmissionTreeNode(kid_st_dict, parent=self) for kid_st_dict in st_dict["kids"]]

    def _print(self, s):
        if self.verbose:
            print(s)

    def __str__(self):
        num_descendants = len(self.convert_to_list()) - 1

        contents = f"""
        ST {self.id}
            is {'' if self.is_root else 'not'} root
            is {'' if self.active else 'not'} active
            {'parent: ' + self.parent.get_id() if self.parent != None else ''}
            has {num_descendants} descendants
        """
        return contents

    def print_kids(self):
        contents = f"Kids of ST {self.id}:\n"
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

    def get_parent(self):
        return self.parent

    def get_is_root(self):
        return self.is_root
    
    def get_kids(self):
        return self.kids

    def set_kids(self, new_kids):
        self.kids = new_kids

    """
        Get a list representing this node's ancestor path.
    """
    def get_ancestor_path(self):
        return [self] if self.is_root else [*self.parent.get_ancestor_path(), self]

    """
        Add a kid to this node, given an id.
    """
    def add_kid(self, kid_id):
        kid = SubmissionTreeNode({"id": kid_id, "kids": []}, parent=self)
        new_kids = [*self.kids, kid]
        self.kids = new_kids

    """
        Check if a submission of a given id is present in this node's descendants
    """
    def check_contains_descendant(self, desc_id):
        f = lambda n: n["st_node"].get_id() == desc_id or n["desc_result"]
        reduce_kids_f = lambda acc, n: n or acc
        reduce_kids_acc = False
        return self.dfs(f, reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc)

    """
        Get a descendant submission of this node, given its id.
    """
    def get_descendant(self, desc_id):
        f = lambda n: n["st_node"] if n["st_node"].get_id() == desc_id else n["desc_result"]
        reduce_kids_f = lambda acc, n: n if n != None else acc
        reduce_kids_acc = None
        return self.dfs(f, reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc)
    
    """
        Add a kid to some descendant of this node, given a child and parent id.
    """
    def add_descendant(self, desc_id, kid_id):
        parent = self.get_descendant(desc_id)
        parent.add_kid(kid_id)

    """
        Remove a descendant of this node, given an ID.
        If successful, return true, if not present, or the retrieved item is a root, return false
    """
    def remove_descendant(self, desc_id):
        submission = self.get_descendant(desc_id)
        if submission == None:
            return False
        else:
            parent = submission.get_parent()
            if parent == None:
                return False
            else:
                new_kids = [kid for kid in parent.get_kids() if kid.get_id() != desc_id]
                parent.set_kids(new_kids)
                return True

    """
        Get a flattened list of this node and all of its descendants.
    """
    def convert_to_list(self):
        return self.dfs(lambda c: [c["st_node"], *c["desc_result"]], reduce_kids_f=lambda acc, c: [*acc, *c], reduce_kids_acc=[])

    def get_descendant_list(self):
        return self.dfs(lambda c: c["desc_result"] if c["st_node"].get_is_root() else [c["st_node"], *c["desc_result"]], reduce_kids_f=lambda acc, c: [*acc, *c], reduce_kids_acc=[])

    """
        Convert the tree back to its original, dict form.
    """
    def convert_to_dict(self):
        return self.dfs(lambda c: {"id": c["st_node"].get_id(), "kids": c["desc_result"]}, reduce_kids_f=lambda acc, c: [*acc, c], reduce_kids_acc=[])


    """
        Fetch the full submission object of this node with provided data sources
    """
    def fetch_submission_object(self):
        if self.is_root:
            return self.root_factory(self.id)
        else:
            return self.stem_factory(self.id)
        
    """
        Check all items in this tree
        to see whether all of the data necessary to 
        generate a full feature set with it is present, and 
        if not, remove it.
    """
    def clean(self, checker=None):
        clean_kids = []
        for kid in self.kids:
            try:
                kid_object = kid.fetch_submission_object()
                if kid_object.check(checker=checker):
                    kid.clean(checker=checker)
                    clean_kids.append(kid)
            except Exception as e:
                continue
        self.set_kids(clean_kids)


    """
        Iterate through the descendants of this tree via a DFS, with provided data sources
    """
    def dfs(self, f,  filter_f=None, reduce_kids_f=None, reduce_kids_acc=None):

        f_inp = {
            "st_node": self,
            "sub_obj": None,
            "desc_result": None
        }
        
        f_inp["sub_obj"] = self.fetch_submission_object()

        if filter_f != None:
            filter_res = filter_f(f_inp)
            if filter_res == False:
                return None

        kid_results = [kid.dfs(f, filter_f=filter_f, reduce_kids_f=reduce_kids_f,reduce_kids_acc=reduce_kids_acc) for kid in self.kids] 

        if reduce_kids_f != None:
            reduced = functools.reduce(reduce_kids_f, kid_results, reduce_kids_acc)
            f_inp["desc_result"] = reduced

        return f(f_inp)

    def iter_dfs(self):
        yield self.fetch_submission_object()
        for kid in self.kids:
            yield from kid.iter_dfs()

    def iter_dfs_branches(self, branch=None):
        yield branch
        
        for kid in self.kids:
            branch.push_stem(kid.fetch_submission_object())
            yield from kid.iter_dfs_branches(branch=branch)
            branch.pop_stem()


"""
    An exception class for all PRF related errors.
"""
class SubmissionForestError(Exception):
    def __init__(self, message):
        super().__init__(message)

"""
    A class to hold all of the submission trees present in the dataset.
"""

class SubmissionForest:
    def __init__(self, name, st_dict_list, root_factory, stem_factory, verbose=False):
        self.name = name
        self.roots = [SubmissionTreeNode(st_dict, root_factory, stem_factory, verbose=verbose) for st_dict in st_dict_list]
        self.verbose = verbose
    
    def _print(self, s):
        if self.verbose: 
            print(s)

    def __str__(self):
        contents = "Submission Forest:\n"
        contents += "\t" + f"Contains {len(self.roots)} roots.\n"
        return contents
        
    def get_roots(self):
        return self.roots

    def set_roots(self, new_roots):
        self.roots = new_roots

    """
        Get the current potential response forest in the original list format.
    """
    def convert_to_st_dict_list(self):
        st_dict_list = [root.convert_to_dict() for root in self.roots]
        return st_dict_list

    """
        Check whether or not a submission with a given id is present in the forest.
        If there are multiple present, raise an error.
    """
    def check_contains_submission(self, sub_id):
        filtered_roots = [root for root in self.roots if root.check_contains_descendant(sub_id)]
        if len(filtered_roots) == 1:
            return True
        elif len(filtered_roots) == 0:
            return False
        else:
            raise SubmissionForestError(f"Error: item with id {sub_id} found in multiple roots of {self}.")

    """
        Get an submission's root if it exists among member trees, otherwise, raise an error.
    """
    def get_root_of_submission(self, sub_id):
        filtered_roots = [root for root in self.roots if root.check_contains_descendant(sub_id)]
        if len(filtered_roots) == 0:
            raise SubmissionForestError(f"Error: Submission with id {sub_id} not found in {self}")
        elif len(filtered_roots) == 1:
            return filtered_roots[0]
        else:
            raise SubmissionForestError(f"Error: Submission with id {sub_id} found in multiple roots of {self}")
    
    """
        Get an submission's node if it exists among member trees, otherwise, raise an error.
    """
    def get_submission(self, sub_id):
        potential_submissions = [root.get_descendant(sub_id) for root in self.roots]
        filtered_submissions = [res for res in potential_submissions if res != None]
        if len(filtered_submissions) == 0:
            raise SubmissionForestError(f"Error: Submission with id {sub_id} not found in {self}")
        elif len(filtered_submissions) == 1:
            return filtered_submissions[0]
        else: 
            raise SubmissionForestError(f"Error: Submission with id {sub_id} found in multiple roots of {self}")

    """
        Get a list of submissions.
    """
    def get_submission_list(self, sub_id_list):
        submissions = [self.get_submission(sub_id) for sub_id in sub_id_list]
        return submissions

    """
        Get a full flattened list of all submissions in this forest.
    """
    def convert_to_flattened_list(self):
        all_submissions = functools.reduce(lambda acc, r: [*acc, *r], [root.convert_to_list() for root in self.roots], [])
        return all_submissions

    """
        Remove a submission from this forest of a given id.
    """
    def remove_submission(self, sub_id):
        root_of_item = self.get_root_of_submission(sub_id)
        if root_of_item.get_id() == sub_id:
            self.remove_root(sub_id)
        else:
            root_of_item.remove_descendant(sub_id)

    """
        Remove a list of items, by their ids.
        Handle the not found error if thrown as if this is done in batches,
        parent comments may be removed first and later children may not be found, which is fine
    """
    def remove_submission_list(self, sub_id_list):
        for sub_id in sub_id_list:
            try:
                self.remove_item(sub_id)
            except PotentialResponseForestError as e:
                print(f"Submission with id {sub_id} has already been removed. Continuing.")
                continue

    """
        Add a root to the forest, given its ID.
    """
    def add_root(self, root_id):
        new_root = SubmissionTreeNode({"id": root_id, "kids": []})
        new_roots = [*self.roots, new_root]
        self.set_roots(new_roots)

    """
        Add a list of new roots to the forest, given their ids
    """
    def add_root_list(self, root_id_list):
        for root_id in root_id_list:
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
    def remove_root_list(self, root_id_list):
        for root_id in root_id_list:
            self.remove_root(root_id)

    """
        Activate all potential response nodes made prior to a given time.
    """
    def activate_before_time(self, time):
        for root in self.roots:
            root.activate_before_time(time)

    """
        Run a DFS on all roots, with given parameters.
    """
    def dfs_roots(self, f, filter_f=None, reduce_kids_f=None, reduce_kids_acc=None):
        return [root.dfs(f, filter_f=filter_f,
            reduce_kids_f=reduce_kids_f, reduce_kids_acc=reduce_kids_acc) for root in self.roots]

    def iter_dfs(self):
        for root in self.roots:
            yield from root.iter_dfs()

    def iter_bfs(self):
        queue = deque(self.roots)
        while queue:
            node = queue.popleft()
            yield node.fetch_submission_object()
            for kid in node.kids:
                queue.append(kid)

    def iter_roots(self):
        for root in self.roots:
            yield root.fetch_submission_object()

    def iter_dfs_branches(self):
        for root in self.roots:
            yield from root.iter_dfs_branches(branch=Branch(root.fetch_submission_object()))

    """
        Clean all roots.
    """
    def clean(self, root_checker=None, stem_checker=None):
        clean_roots = []
        for root in self.roots:
            try:
                root_object = root.fetch_submission_object()
                if root_object.check(checker=root_checker):
                    root.clean(checker=stem_checker)
                    clean_roots.append(root)
            except Exception as e:
                continue

        self.set_roots(clean_roots)
