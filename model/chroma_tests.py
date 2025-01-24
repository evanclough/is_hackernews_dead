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

        cls.insertion_num = 999
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
        user_profile = self.dataset.user_pool.fetch_user_profile(self.test_username, sqlite_db=self.dataset.sqlite_db)
        self.dataset.chroma_db.embed_user_profiles([user_profile])

    """
        Test retrieving embeddings for a user profile
    """
    def test_retrieve_user_embeddings(self):
        result = self.dataset.chroma_db.get_user_profile_embeddings(self.test_username)
        print(result)
    
    """
        Test creating embeddings for a post
    """
    def test_create_post_embeddings(self):
        post = self.dataset.prf.get_item(self.insertion_num)
        post_contents = post.fetch_contents(sqlite_db=self.dataset.sqlite_db)
        self.dataset.chroma_db.embed_posts([post_contents])

    """
        Test retreiving embedings for a post
    """
    def test_retrieve_post_embeddings(self):
        result = self.dataset.chroma_db.get_post_embeddings(self.insertion_num)
        print(result)

        """
        Test creating embeddings for a comment
    """
    def test_create_comment_embeddings(self):
        comment = self.dataset.prf.get_item(self.insertion_num + 1)
        comment_contents = comment.fetch_contents(sqlite_db=self.dataset.sqlite_db)
        self.dataset.chroma_db.embed_comments([comment_contents])

    """
        Test retreiving embedings for a post
    """
    def test_retrieve_comment_embeddings(self):
        result = self.dataset.chroma_db.get_comment_embeddings(self.insertion_num + 1)
        print(result)

if __name__ == '__main__':
    unittest.main()