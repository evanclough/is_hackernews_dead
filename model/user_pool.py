"""
    A file to hold the user pool class, used by the dataset to hold
    its users.
"""

"""
    An exception class for all user pool related errors.
"""
class UserPoolError(Exception):
    def __init__(self, message):
        super().__init__(message)

class UserPool:
    def __init__(self, name, existing_username_list=None):
        self.name = name
        self.active = False
        if existing_username_list != None:
            self._init_from_existing(existing_username_list)

    """
        Initialize, given a username list from an existing dataset in the format 
        from the data module.
    """
    def _init_from_existing(self, existing_username_list):
        self.usernames = existing_username_list

    def __str__(self):
        return f"user pool {self.name}"

    def get_usernames(self):
        return self.usernames

    def set_usernames(self, usernames):
        self.usernames = usernames

    """
        Get a user from this user pool of a given username.
        Raise an error if they're not present.
    """
    def fetch_user_profile(self, username, sqlite_db):
        if self.check_contains_user(username):
            return sqlite_db.get_user_profile(username)
        else:
            raise UserPoolError(f"Error: attempt to get user of username {username} not present in the user pool.")

    """
        Fetch the profile of a list of users, given their usernames.
    """
    def fetch_some_user_profiles(self, username_list, sqlite_db):
        user_profiles = [self.fetch_user_profile(username, sqlite_db) for username in username_list]

        return user_profiles

    """
        Fetch the profiles of all users in the user pool.
    """
    def fetch_all_user_profiles(self, sqlite_db):
        return self.fetch_some_user_profiles(self.usernames, sqlite_db)

    """
        Check if this user pool contains a user with a given username.
        If multiple users with the same username are present, raise an error.
    """
    def check_contains_user(self, username):
        filtered_users = [u for u in self.usernames if u == username]
        if len(filtered_users) == 1:
            return True
        elif len(filtered_users) == 0:
            return False
        else:
            raise UserPoolError(f"Multiple users with username {username} present in the user pool.")

    """
        Add a list of usernames to the user pool, given their usernames
    """
    def add_usernames(self, usernames):
        new_usernames = [*self.usernames, *usernames]
        self.set_usernames(new_usernames)

    """
        Remove a list of usernames from the user pool
    """
    def remove_usernames(self, usernames):
        new_usernames = [u for u in self.usernames if not (u in usernames)]
        self.set_usernames(new_usernames)

    """
        Clean this user pool by checking each user and removing all
        who fail.
    """
    def clean(self, sqlite_db):
        user_profiles = self.fetch_all_user_profiles(sqlite_db)
        clean_usernames = [user_profile.username for user_profile in user_profiles if user_profile.check(sqlite_db)]
        self.usernames = clean_usernames
    
