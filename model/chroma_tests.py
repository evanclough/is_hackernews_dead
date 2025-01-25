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
        
        cls.test_dataset_name = "CHROMA_TEST"

        cls.dataset = dataset.Dataset(cls.test_dataset_name, existing_dataset_name=cls.test_dataset_name)

        cls.insertion_num = 888
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
            "about": "test_about",
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

        self.dataset.chroma_db.embed_datatype("user_profile", [user_dict])

        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("user_profile", [self.test_username])[0]

        self.assertTrue(len(retrieved["about"]) == 1)
        self.assertTrue(len(retrieved["text_samples"]) == 2)
        self.assertTrue(len(retrieved["beliefs"]) == 2)
        self.assertTrue(len(retrieved["interests"]) == 2)

    """
        Test removing embeddings fo ra user.
    """
    def test_remove_user_embeddings(self):
        self.dataset.chroma_db.remove_embeddings_for_datatype("user_profile", [self.test_username])
        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("user_profile", [self.test_username])[0]
        self.assertTrue(len(retrieved["about"]) == 0)
        self.assertTrue(len(retrieved["text_samples"]) == 0)
        self.assertTrue(len(retrieved["interests"]) == 0)
        self.assertTrue(len(retrieved["beliefs"]) == 0)

    """
        Test updating embeddings for a user.
    """
    def test_update_user_embeddings(self):
        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("user_profile", [self.test_username])[0]
        print(retrieved["about"])

        user_dict = {
            "username": self.test_username,
            "about": "test_about_2",
            "karma": 4,
            "created": "12354",
            "user_class": "test",
            "post_ids": [],
            "comment_ids": [],
            "favorite_post_ids": [],
            "text_samples": ["test999"],
            "interests": ["test999", "tes888", "test777"],
            "beliefs": ["test124123"],
            "misc_json": []
        }
        self.dataset.chroma_db.update_embeddings_for_datatype("user_profile", [user_dict], atts=["interests"])
        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("user_profile", [self.test_username])[0]
        self.assertTrue(len(retrieved["interests"]) == 3)
        print(retrieved["about"])

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

        self.dataset.chroma_db.embed_datatype("post", [post_dict])

        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("post", [self.insertion_num])[0]
        self.assertTrue(len(retrieved["url_content"]) == 1)
        self.assertTrue(len(retrieved["title"]) == 1)
        self.assertTrue(len(retrieved["text"]) == 1)

    """
        Test removing embeddings for a post.
    """
    def test_remove_post_embeddings(self):
        result = self.dataset.chroma_db.remove_embeddings_for_datatype("post", [self.insertion_num])

        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("post", [self.insertion_num])[0]
        self.assertTrue(len(retrieved["url_content"]) == 0)
        self.assertTrue(len(retrieved["title"]) == 0)
        self.assertTrue(len(retrieved["text"]) == 0)

    """
        Test updating embeddings for a post
    """
    def test_update_post_embeddings(self):
        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("post", [self.insertion_num])[0]
        print(retrieved["text"])

        post_dict = {
            "by": self.test_username,
            "id": self.insertion_num,
            "time": str(int(time.time())),
            "text": "test post text 2",
            "title": "test post title 2",
            "url": "test url",
            "url_content": "test url content 2",
            "score": 123,
            "misc_json": []
        }

        self.dataset.chroma_db.update_embeddings_for_datatype("post", [post_dict])

        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("post", [self.insertion_num])[0]
        self.assertTrue(len(retrieved["url_content"]) == 1)
        self.assertTrue(len(retrieved["title"]) == 1)
        self.assertTrue(len(retrieved["text"]) == 1)
        print(retrieved["text"])


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

        self.dataset.chroma_db.embed_datatype("comment", [comment_dict])

        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("comment", [self.insertion_num + 1])[0]
        self.assertTrue(len(retrieved["text"]) == 1)

    """
        Test removing embeddings fo ra comment.
    """
    def test_remove_comment_embeddings(self):
        self.dataset.chroma_db.remove_embeddings_for_datatype("comment", [self.insertion_num + 1])

        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("comment", [self.insertion_num + 1])[0]
        self.assertTrue(len(retrieved["text"]) == 0)

    """
        Test updating embeddings for a comment
    """
    def test_update_comment_embeddings(self):
        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("comment", [self.insertion_num + 1])[0]
        print(retrieved["text"])
        comment_dict = {
            "by": self.test_username,
            "id": self.insertion_num + 1,
            "time": str(int(time.time())),
            "text": "test text 234",
            "misc_json": [],
            "parent_id": self.insertion_num
        }

        self.dataset.chroma_db.update_embeddings_for_datatype("comment", [comment_dict])

        retrieved = self.dataset.chroma_db.get_embeddings_for_datatype("comment", [self.insertion_num + 1])[0]
        self.assertTrue(len(retrieved["text"]) == 1)
        print(retrieved["text"])


    

if __name__ == '__main__':
    unittest.main()