"""
    A file to hold the user pool class, used by the dataset to hold
    its users.
"""

"""
    An exception class for all user pool related errors.
"""
class UserNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)

class MulitpleUsersFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)

class UserPool:
    def __init__(self, name, uid_list, entity_factory, sqlite, chroma, verbose=False):
        self.name = name
        self.active = False
        self.uids = uid_list
        self.entity_factory = entity_factory
        self.sqlite = sqlite
        self.chroma = chroma
        self.verbose = verbose

    def _print(self, s):
        if self.verbose:
            print(s)

    def __str__(self):
        contents =  "User Pool:\n"
        contents += "\t" + f"Contains {len(self.uids)} users." + "\n"
        return contents

    def print_uids(self):
        contents = f"uids in user pool {self.name}"
        for uid in self.uids:
            contents += uids + "\n"        

    def get_uids(self):
        return self.uids

    def set_uids(self, uids):
        self.uids = uids

    """
        Get a user object of a given uid from this user pool, with given data sources.
        Raise an error if they're not present.
    """
    def fetch_user_object(self, uid, load={}):
        if self.check_contains_user(uid):
            return self.entity_factory("user", uid, load=load)
        else:
            raise UserNotFoundError(f"Error: attempt to fetch user object with uid {uid} not present in the user pool.")

    """
        Fetch the profile of a list of users, given their uids.
    """
    def fetch_user_object_list(self, uid_list, load={}):
        users = [self.fetch_user_object(uid, load=load) for uid in uid_list]
        return users

    """
        Fetch the profiles of all users in the user pool.
    """
    def fetch_all_user_objects(self, load={}):
        return [self.entity_factory("user", uid, load=load) for uid in self.uids]

    """
        Check if this user pool contains a user with a given uid.
        If multiple users with the same uid are present, raise an error.
    """
    def check_contains_user(self, uid):
        filtered_uids = [u for u in self.uids if u == uid]
        if len(filtered_uids) == 1:
            return True
        elif len(filtered_uid) == 0:
            return False
        else:
            raise MulitpleUsersFoundError(f"Multiple users with uid {uid} present in the user pool.")

    """
        Add a list of uids to the user pool, given their uids
    """
    def add_uids(self, uids):
        new_uids = self.uids + uids
        self.set_uids(new_uids)

    """
        Remove a list of uids from the user pool
    """
    def remove_uids(self, uids):
        new_uids = [u for u in self.uids if not (u in uids)]
        self.set_uids(new_uids)

    """
        Clean this user pool by checking each user (by provided sources) and removing all
        who fail.
    """
    def clean(self, load={}, checklist={}, derived_kwargs={}):
        all_users = self.fetch_all_user_objects(load=load)
        clean_uids = [user.get_id() for user in all_users if user.check(checklist=checklist)]
        self.set_uids(clean_uids)
    
