"""
    Unit tests for the dataset class.
"""

import unittest
import time
import random

import utils
import sqlite_utils
import classes

class TestDataset(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dataset = classes.Dataset("TEST", existing_dataset_name="CURRENT_TEST")
        cls.dataset.initialize_for_run()
        cls.insertion_num = 888888
        print(f"insertion number: {cls.insertion_num}")
    
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

        self.dataset.add_users([user_dict])
        self.assertIsNotNone(self.dataset.user_pool.get_user(f"test_username{self.insertion_num}"))


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

        self.dataset.add_root_posts([post_dict])
        
        self.assertIsNotNone(self.dataset.get_member_item(self.insertion_num))

    
    """
        Test inserting a comment to a root post.
    """
    def test_comment_insertion_to_root(self):

        comment_dict = {
            "by": f"test_username{self.insertion_num}",
            "id": self.insertion_num + 1,
            "time": str(int(time.time())),
            "text": "test text",
            "misc_json": []
        }

        self.dataset.add_comment(comment_dict, self.insertion_num)

        self.assertIsNotNone(self.dataset.get_member_item(self.insertion_num + 1))

        
    """
        Test inserting a comment under an existing comment.
    """
    def test_comment_insertion_to_leaf(self):
        comment_dict = {
            "by": f"test_username{self.insertion_num}",
            "id": self.insertion_num + 2,
            "time": str(int(time.time())),
            "text": "test text",
            "misc_json": []
        }
        self.dataset.add_comment(comment_dict, self.insertion_num + 1)

        self.assertIsNotNone(self.dataset.get_member_item(self.insertion_num + 2))

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
        self.assertTrue(self.dataset.remove_post(post_to_remove))

    """
        Test removing a comment from the dataset.
    """
    def test_comment_removal(self):
        comment_to_remove = self.insertion_num + 1
        """
            get_descendants doesnt work!! in either of them!!
        """
        self.assertTrue(self.dataset.remove_comment(comment_to_remove))



if __name__ == '__main__':
    unittest.main()