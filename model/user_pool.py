"""
    A file to hold the user pool class, used by the dataset to hold
    its users.
"""

import classes

"""
    An exception class for all user pool related errors.
"""
class UserPoolError(Exception):
    def __init__(self, message):
        super().__init__(message)

class UserPool:
    def __init__(self, name, username_list):
        self.name = name
        self.active = False
        self.usernames = username_list

    def __str__(self):
        contents =  f"""
        User pool {self.name}:
            Number of users: {len(self.usernames)}
        """
        return contents

    def print_usernames(self):
        contents = f"Usernames in user pool {self.name}"
        for username in self.usernames:
            contents += username + "\n"        

    def get_usernames(self):
        return self.usernames

    def set_usernames(self, usernames):
        self.usernames = usernames

    """
        Get a user from this user pool of a given username, with given data sources.
        Raise an error if they're not present.
    """
    def fetch_user_profile(self, username, sqlite_db=None, chroma_db=None):
        if self.check_contains_user(username):
            return classes.UserProfile(username, sqlite_db=sqlite_db, chroma_db=chroma_db)
        else:
            raise UserPoolError(f"Error: attempt to get user of username {username} not present in the user pool.")

    """
        Fetch the profile of a list of users, given their usernames.
    """
    def fetch_some_user_profiles(self, username_list, sqlite_db=None, chroma_db=None):
        user_profiles = [self.fetch_user_profile(username, sqlite_db=sqlite_db, chroma_db=chroma_db) for username in username_list]

        return user_profiles

    """
        Fetch the profiles of all users in the user pool.
    """
    def fetch_all_user_profiles(self, sqlite_db=None, chroma_db=None):
        return self.fetch_some_user_profiles(self.usernames, sqlite_db=sqlite_db, chroma_db=chroma_db)

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
    
