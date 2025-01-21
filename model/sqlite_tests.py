"""
    Unit tests for the dataset class's interaction with sqlite.
"""

import unittest
import time
import json

import utils
import dataset

class SqliteTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dataset = dataset.Dataset("TEST", existing_dataset_name="CURRENT_TEST")
        cls.dataset.initialize_for_run()
        cls.insertion_num = 9999
        print(f"insertion number: {cls.insertion_num}")

    """
        Test the initialization of the dataset.
        (doesn't actually do anything, really just testing the set up class method)
    """
    def test_initialization(self):
        self.assertEqual(self.dataset.get_name(), "TEST")

    """
        Test inserting a new user to the user pool. (no post history)
    """
    def test_new_user_insertion(self):
        user_dict = {
            "username": f"test_username{self.insertion_num}",
            "about": "test about",
            "karma": 4,
            "created": "12354",
            "user_class": "test",
            "post_ids": [],
            "comment_ids": [],
            "favorite_post_ids": [],
            "text_samples": [],
            "interests": [],
            "beliefs": [],
            "misc_json": []
        }

        self.assertTrue(self.dataset.add_users([user_dict]))

    """
        Test inserting a post to the dataset.
    """
    def test_post_insertion(self):

        post_dict = {
            "by": f"test_username{self.insertion_num}",
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
            "by": f"test_username{self.insertion_num}",
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
            "by": f"test_username{self.insertion_num}",
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
        username_to_remove = f"test_username{self.insertion_num}"
        self.assertTrue(self.dataset.remove_users([username_to_remove]))

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
        username_to_remove = f"test_username{self.insertion_num}"
        self.assertTrue(self.dataset.remove_users([username_to_remove], remove_posts=True, remove_comments=True))

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


if __name__ == '__main__':
    unittest.main()