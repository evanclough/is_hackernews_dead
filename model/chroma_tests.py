"""
    Unit tests for the dataset class's interaction with chroma
"""

import unittest
import time
import json

import utils
import dataset

class ChromaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        
        cls.test_dataset_name = "SCRATCH_TEST"

        cls.dataset = dataset.Dataset(cls.test_dataset_name, existing_dataset_name=cls.test_dataset_name)
        cls.dataset.initialize_for_run()

        cls.insertion_num = 158725897
        cls.test_username = f"test_username{cls.insertion_num}"

        print(f"Running tests on existing dataset {cls.test_dataset_name}...")
        print(f"test insertion number: {cls.insertion_num}")

    """
        Test initialization (run set up class)
    """
    def test_init(self):
        self.assertIsNotNone(self.dataset)

    """
        Test creating embeddings for a user profile
    """
    def test_create_user_embeddings(self):
        user_dict = {
            "username": self.test_username,
            "about": "test",
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

        self.dataset.chroma_db.embed_user_profiles([user_dict])

        retrieved = self.dataset.chroma_db.get_user_profile_embeddings(self.test_username)
        self.assertTrue(len(retrieved["about"]) == 1)


    """
        Test removing embeddings fo ra user.
    """
    def test_remove_user_embeddings(self):
        self.dataset.chroma_db.remove_user_profile_embeddings([self.test_username])

        retrieved = self.dataset.chroma_db.get_user_profile_embeddings(self.test_username)
        self.assertTrue(len(retrieved["about"]) == 0)
    
    """
        Test creating embeddings for a post
    """
    def test_create_post_embeddings(self):
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

        self.dataset.chroma_db.embed_posts([post_dict])

        retrieved = self.dataset.chroma_db.get_post_embeddings(self.insertion_num)
        self.assertTrue(len(retrieved["url_content"]) == 1)

    """
        Test removing embeddings for a post.
    """
    def test_remove_post_embeddings(self):
        result = self.dataset.chroma_db.remove_post_embeddings([self.insertion_num])

        retrieved = self.dataset.chroma_db.get_post_embeddings(self.insertion_num)
        self.assertTrue(len(retrieved["url_content"]) == 0)

        """
        Test creating embeddings for a comment
    """
    def test_create_comment_embeddings(self):
        comment_dict = {
            "by": self.test_username,
            "id": self.insertion_num + 1,
            "time": str(int(time.time())),
            "text": "test text",
            "misc_json": [],
            "parent_id": self.insertion_num
        }

        self.dataset.chroma_db.embed_comments([comment_dict])

        retrieved = self.dataset.chroma_db.get_comment_embeddings(self.insertion_num + 1)
        self.assertTrue(len(retrieved["text_content"]) == 1)

    """
        Test removing embeddings fo ra comment.
    """
    def test_remove_comment_embeddings(self):
        self.dataset.chroma_db.remove_comment_embeddings([self.insertion_num + 1])

        retrieved = self.dataset.chroma_db.get_comment_embeddings(self.insertion_num + 1)
        self.assertTrue(len(retrieved["text_content"]) == 0)

if __name__ == '__main__':
    unittest.main()