"""
    General unit tests for the dataset class.
"""

import unittest
import time
import json

import utils
import dataset
import HN_entities

"""
    Tests for initializing the dataset with various options.
"""
class InitTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.entity_classes = {
            "user": HN_entities.HNUser,
            "root": HN_entities.HNPost,
            "branch": HN_entities.HNComment
        }
        cls.test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
        cls.test_dataset = dataset.Dataset(cls.test_dataset_name, cls.entity_classes, verbose=True)


        print(f"Running tests on dataset {cls.test_dataset_name}...")

    def get_cuo(self):
        def create_user_object(uid):
            return self.test_dataset.entity_factory("user", uid, load={'base': {'sqlite': self.test_dataset.sqlite}})
        return create_user_object

    def get_cpo(self):
        def create_post_object(post_id):
            return self.test_dataset.entity_factory("root", post_id, load={'base': {'sqlite': self.test_dataset.sqlite}})
        return create_post_object
        
    def get_cco(self):
        def create_comment_object(comment_id):
            return self.test_dataset.entity_factory("branch", comment_id, load={'base': {'sqlite': self.test_dataset.sqlite}})
        return create_comment_object

    
    def get_HN_derived_sload_dict(self):
        return 

    """
        Test loading in a dataset.
    """
    def test_load(self):
        self.assertIsNotNone(self.test_dataset)

    """
        Test loading base attributes for the user pool.
    """
    def test_base_upl(self):
        self.test_dataset.user_pool.fetch_all_user_objects(load={'base': {'sqlite': self.test_dataset.sqlite}})

    """
        Test loading hn derived attributes
    """
    def test_HN_derived_upl(self):
        load_dict = {
            'base': {
                'sqlite': self.test_dataset.sqlite
            },
            'derived': {
                'sqlite': self.test_dataset.sqlite,
                'other': {
                    'create_post_f': self.get_cpo(),
                    'create_comment_f': self.get_cco(),
                    'skip_submission_errors': True
                }
            }
        }
        self.test_dataset.user_pool.fetch_all_user_objects(load=load_dict)

    """
        Test loading base attributes for the submission forest.
    """
    def test_base_sfl(self):
        self.test_dataset.sf.dfs_roots(lambda a: a, load={'base': {'sqlite': self.test_dataset.sqlite}})

    """
        Test loading hn derived attributes
    """
    def test_HN_derived_sfl(self):
        load_dict = {
            'base': {
                'sqlite': self.test_dataset.sqlite
            },
            'derived': {
                'sqlite': self.test_dataset.sqlite,
                'other': {
                    'create_user_f': self.get_cuo()
                }
            }
        }
        self.test_dataset.sf.dfs_roots(lambda a: a, load=load_dict)


    """
        Test storing embeddings for a hn dataset.
    """
    def test_store_embeddings(self):
        

        user_source_dict = {
            'create_post_f': self.get_cpo(),
            'create_comment_f': self.get_cco(),
            'skip_submission_errors': True
        }

        submission_source_dict= {
            'create_user_f': self.get_cuo()
        }

        user_checklist ={
            "base": {},
            "derived": {
                "submission_checklist": {'base': {}}
            }
        }
        submission_checklist ={
            "base": {},
            "derived": {
                "author_checklist": {'base': {}}
            }
        }

        self.test_dataset.embed(user_derived_sources=user_source_dict, user_checklist=user_checklist, submission_derived_sources=submission_source_dict, submission_checklist=submission_checklist)

        self.assertIsNotNone(self.test_dataset)

    def test_embeddings_upl(self):
        load_dict = {
            'base': {
                'sqlite': self.test_dataset.sqlite
            },
            'derived': {
                'sqlite': self.test_dataset.sqlite,
                'other': {
                    'create_post_f': self.get_cpo(),
                    'create_comment_f': self.get_cco(),
                    'skip_submission_errors': True
                }
            },
            "embeddings": {
                "chroma": self.test_dataset.chroma
            }
        }
        self.test_dataset.user_pool.fetch_all_user_objects(load=load_dict)

    def test_embeddings_sfl(self):
        load_dict = {
            'base': {
                'sqlite': self.test_dataset.sqlite
            },
            'derived': {
                'sqlite': self.test_dataset.sqlite,
                'other': {
                    'create_user_f': self.get_cuo()
                }
            },
            "embeddings": {
                "chroma": self.test_dataset.chroma
            }
        }

        self.test_dataset.sf.dfs_roots(lambda a: a, load=load_dict)


"""
    Test crud operations on a given dataset.
    If the dataset at the designated location contains a chroma database, 
    embeddings will be created/updated/deleted, if not, they will not.
"""
class CrudTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
        cls.dataset = dataset.Dataset(cls.test_dataset_name, existing_dataset_name=cls.test_dataset_name, verbose=True)
        cls.insertion_num = 55555
        cls.test_username = f"test_username{cls.insertion_num}"
        print(f"Running sqlite tests on existing dataset {cls.test_dataset_name}...")
        print(f"test insertion number: {cls.insertion_num}")

    """
        Test the initialization of the dataset.
        (doesn't actually do anything)
    """
    def test_init(self):
        self.assertIsNotNone(self.dataset)

    """
        Test inserting a new user to the user pool. (no post history)
    """
    def test_user_insertion(self):
        user_dict = {
            "username": self.test_username,
            "about": "test about",
            "karma": 4,
            "created": int(time.time()),
            "user_class": "test",
            "post_ids": [],
            "comment_ids": [],
            "favorite_post_ids": []
        }

        self.assertTrue(self.dataset.add_users([user_dict]))

    """
        Test inserting a post to the dataset.
    """
    def test_post_insertion(self):

        post_dict = {
            "by": self.test_username,
            "id": self.insertion_num,
            "time": int(time.time()),
            "text": "test post text",
            "title": "test post title",
            "url": "test url",
            "url_content": "test url content",
            "score": 123
        }

        self.assertTrue(self.dataset.add_root_posts([post_dict], update_author_profile=True))
    
    """
        Test inserting a comment to a root post.
    """
    def test_comment_insertion_to_root(self):

        comment_dict = {
            "by": self.test_username,
            "id": self.insertion_num + 1,
            "time": int(time.time()),
            "text": "test text",
            "parent": self.insertion_num
        }

        self.assertTrue(self.dataset.add_leaf_comments([comment_dict], update_author_profile=True))
        
    """
        Test inserting a comment under an existing comment.
    """
    def test_comment_insertion_to_leaf(self):
        comment_dict = {
            "by": self.test_username,
            "id": self.insertion_num + 2,
            "time": int(time.time()),
            "text": "test text",
            "parent": self.insertion_num + 1
        }

        self.assertTrue(self.dataset.add_leaf_comments([comment_dict], update_author_profile=True))

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
        self.assertTrue(self.dataset.remove_comments([comment_to_remove]))

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
        comment_to_remove = self.insertion_num + 1
        self.assertTrue(self.dataset.remove_comments([comment_to_remove], update_author_profile=True))

    """
        Run all of the insertion tests in the necessary order.
    """
    def test_insertion(self):
        self.test_user_insertion()
        self.test_post_insertion()
        self.test_comment_insertion_to_root()
        self.test_comment_insertion_to_leaf()

    """
        Run the standard removal tests in the best order.
    """
    def test_removal(self):
        self.test_full_comment_removal()
        self.test_full_post_removal()
        self.test_full_user_removal()
    
    """
        Run a full test of all CRUD capabilities.
    """
    def test_full(self):
        self.test_insertion()
        self.test_removal()

if __name__ == '__main__':
    unittest.main()