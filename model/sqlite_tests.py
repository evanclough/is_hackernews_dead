"""
    Unit tests for the dataset class's interaction with sqlite.
"""

import unittest
import time
import json

import utils
import dataset
import feature_extraction

class SqliteTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        
        cls.test_dataset_name = "SCRATCH_TEST"

        cls.dataset = dataset.Dataset(cls.test_dataset_name, existing_dataset_name=cls.test_dataset_name, use_openai_client=True)
        cls.dataset.initialize_for_run()

        cls.insertion_num = 55555
        cls.test_username = f"test_username{cls.insertion_num}"
        print(f"Running tests on existing dataset {cls.test_dataset_name}...")
        print(f"test insertion number: {cls.insertion_num}")

    """
        Test the initialization of the dataset.
        (doesn't actually do anything, really just testing the set up class method)
    """
    def test_init(self):
        self.assertIsNotNone(self.dataset)

    """
        Test inserting a new user to the user pool. (no post history)
    """
    def test_new_user_insertion(self):
        user_dict = {
            "username": self.test_username,
            "about": "test about",
            "karma": 4,
            "created": "12354",
            "user_class": "test",
            "post_ids": [],
            "comment_ids": [],
            "favorite_post_ids": [],
            "text_samples": ["test123", "test1443"],
            "interests": ["test515123", "tes223t1443"],
            "beliefs": ["test124123", "test1443"],
            "misc_json": []
        }

        self.assertTrue(self.dataset.add_users([user_dict]))

    """
        Test inserting a post to the dataset.
    """
    def test_post_insertion(self):

        post_dict = {
            "by": self.test_username,
            "id": self.insertion_num,
            "time": str(int(time.time())),
            "text": "test post text",
            "title": "test post title",
            "url": "test url",
            "url_content": "test url content",
            "score": 123,
            "misc_json": []
        }

        self.assertTrue(self.dataset.add_root_posts([post_dict]))
    
    """
        Test inserting a comment to a root post.
    """
    def test_comment_insertion_to_root(self):

        comment_dict = {
            "by": self.test_username,
            "id": self.insertion_num + 1,
            "time": str(int(time.time())),
            "text": "test text",
            "misc_json": [],
            "parent_id": self.insertion_num
        }

        self.assertTrue(self.dataset.add_leaf_comments([comment_dict]))
        
    """
        Test inserting a comment under an existing comment.
    """
    def test_comment_insertion_to_leaf(self):
        comment_dict = {
            "by": self.test_username,
            "id": self.insertion_num + 2,
            "time": str(int(time.time())),
            "text": "test text",
            "misc_json": [],
            "parent_id": self.insertion_num + 1
        }

        self.assertTrue(self.dataset.add_leaf_comments([comment_dict]))

    """
        Test removing a user from the dataset.
    """
    def test_user_removal(self):
        self.assertTrue(self.dataset.remove_users([self.test_username]))

    """
        Test removing a post from the dataset.
    """
    def test_post_removal(self):
        post_to_remove = self.insertion_num
        self.assertTrue(self.dataset.remove_root_posts([post_to_remove]))

    """
        Test removing a comment from the dataset.
    """
    def test_comment_removal(self):
        comment_to_remove = self.insertion_num + 1
        self.assertTrue(self.dataset.remove_leaf_comments([comment_to_remove]))

    """
        Test removing a user from the dataset, and also removing all of their submissions.
    """
    def test_full_user_removal(self):
        self.assertTrue(self.dataset.remove_users([self.test_username], remove_posts=True, remove_comments=True))

    """
        Test removing a post from the dataset, and also removing it from its author's profile.
    """
    def test_full_post_removal(self):
        post_to_remove = self.insertion_num
        self.assertTrue(self.dataset.remove_root_posts([post_to_remove], update_author_profile=True))
        
    """
        Test removing a comment from the dataset, and also removing it from its author's profile.
    """
    def test_full_comment_removal(self):
        comment_to_remove = self.insertion_num + 2
        self.assertTrue(self.dataset.remove_leaf_comments([comment_to_remove], update_author_profile=True))

    """
        Run all of the insertion tests in the necessary order.
    """
    def test_insertion(self):
        self.test_new_user_insertion()
        self.test_post_insertion()
        self.test_comment_insertion_to_root()
        self.test_comment_insertion_to_leaf()

    """
        Run the standard removal tests in the best order.
    """
    def test_removal(self):
        self.test_user_removal()
        self.test_comment_removal()
        self.test_post_removal()

    """
        Test the addition of new features to a user.
    """
    def test_user_feature_insertion(self):
        self.dataset.add_misc_json_to_user_profile(self.test_username, {"testasldkj": 234})
        self.dataset.populate_text_samples(self.test_username)
        self.dataset.populate_beliefs(self.test_username)
        self.dataset.populate_interests(self.test_username)
        self.dataset.print_user_profile(self.test_username)

    """
        Test the addition of new features to an item.
    """
    def test_item_feature_insertion(self):
        self.dataset.add_misc_json_to_item(self.insertion_num + 1, {"test123": 124})
        self.dataset.print_branch(self.insertion_num + 1)

    """
        Test feature extraction
    """
    def test_feature_extraction(self):
        featurex_test_username = "airstrike"
        print(f"Testing openai feature extraction for {featurex_test_username}...")
        user_profile = self.dataset.user_pool.fetch_user_profile(featurex_test_username,  self.dataset.sqlite_db)
        text_samples_test = feature_extraction.get_text_samples(user_profile, self.dataset.sqlite_db, 5, self.dataset.openai_client, skip_sub_ret_errors=True)
        print(f"text samples: {text_samples_test}")
        beliefs_test = feature_extraction.get_beliefs(user_profile, self.dataset.sqlite_db, 5, 200, self.dataset.openai_client, skip_sub_ret_errors=True)
        print(f"beliefs: {beliefs_test}")
        interests_test = feature_extraction.get_interests(user_profile, self.dataset.sqlite_db, 5, self.dataset.openai_client, skip_sub_ret_errors=True)
        print(f"interests: {interests_test}")

if __name__ == '__main__':
    unittest.main()