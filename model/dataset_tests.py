"""
    General unit tests for the dataset class.
"""

import unittest
import time
import json

import utils
import dataset
import HN_entities
import entities

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
        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True))
        self.test_dataset.user_pool.fetch_all_user_objects(loader)

    """
        Test loading hn derived attributes
    """
    def test_derived_upl(self):

        sub_loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True))
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True), derived=HN_entities.HNUserLoader(post_factory, comment_factory))
        
        self.test_dataset.user_pool.fetch_all_user_objects(loader=loader)

    """
        Test loading base attributes for the submission forest.
    """
    def test_base_sfl(self):
        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True))

        self.test_dataset.sf.dfs_roots(lambda a: a, loader=loader)

    """
        Test loading hn derived attributes
    """
    def test_derived_sfl(self):
        user_loader = entities.EntityLoader(base = entities.BaseLoader(from_sqlite=True))
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True), derived=HN_entities.HNSubmissionLoader(user_factory))

        self.test_dataset.sf.dfs_roots(lambda a: a, loader=loader)


    """
        Test generating embeddings for the user pool.
    """
    def test_embed_up(self):
        sub_loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True))
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True), derived=HN_entities.HNUserLoader(post_factory, comment_factory))
        
        user_objects = self.test_dataset.user_pool.fetch_all_user_objects(loader=loader)
        for user in user_objects:
            user.generate_all_embeddings(self.test_dataset.chroma)

    def test_embed_sf(self):
        user_loader = entities.EntityLoader(base = entities.BaseLoader(from_sqlite=True))
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True), derived=HN_entities.HNSubmissionLoader(user_factory))

        self.test_dataset.sf.dfs_roots(lambda a: a['sub_obj'].generate_all_embeddings(self.test_dataset.chroma), loader=loader)

    def test_load_up_embeddings(self):
        sub_loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True))
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True, embeddings=True), derived=HN_entities.HNUserLoader(post_factory, comment_factory, embeddings=True))
        self.test_dataset.user_pool.fetch_all_user_objects(loader=loader)

        check_dict = {
            "base": {
                "values": True,
                "embeddings": True,
                "checker_params": {}
            },
            "derived": {
                "values": True,
                "embeddings": True,
                "checker_params": {"submission_check_dict": {}}
            }
        }

        self.test_dataset.user_pool.clean(loader, check_dict=check_dict)

    def test_load_sf_embeddings(self):
        user_loader = entities.EntityLoader(base = entities.BaseLoader(from_sqlite=True))
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True, embeddings=True), derived=HN_entities.HNSubmissionLoader(user_factory, embeddings=True))

        self.test_dataset.sf.dfs_roots(lambda a: a, loader=loader)

        check_dict = {
            "base": {
                "values": True,
                "embeddings": True,
                "checker_params": {}
            },
            "derived": {
                "values": True,
                "embeddings": True,
                "checker_params": {"author_check_dict": {}}
            }
        }

        self.test_dataset.sf.clean(loader, check_dict=check_dict)
    


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
        cls.entity_classes = {
            "user": HN_entities.HNUser,
            "root": HN_entities.HNPost,
            "branch": HN_entities.HNComment
        }
        cls.test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
        cls.test_dataset = dataset.Dataset(cls.test_dataset_name, cls.entity_classes, verbose=True)
        cls.insertion_num = 55555
        cls.test_username = f"test_username{cls.insertion_num}"

        print(f"Running sqlite tests on existing dataset {cls.test_dataset_name}...")
        print(f"test insertion number: {cls.insertion_num}")

    """
        Test the initialization of the dataset.
        (doesn't actually do anything)
    """
    def test_init(self):
        self.assertIsNotNone(self.test_dataset)

    """
        Test inserting a new user to the user pool. (no post history)
    """
    def test_user_insertion(self):
        user_dict = {
            "username": self.test_username,
            "about": "test about",
            "karma": 4,
            "created": int(time.time()),
            "user_class": "test user class",
            "post_ids": [],
            "comment_ids": [],
            "favorite_post_ids": []
        }
        sub_loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True))
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        loader = entities.EntityLoader(base=entities.BaseLoader(from_att_dict=True, att_dict=user_dict), derived=HN_entities.HNUserLoader(post_factory, comment_factory))
        new_user = self.test_dataset.entity_factory("user", self.test_username, loader)
        new_user.pupdate_in_sqlite(self.test_dataset.sqlite)
        new_user.pupdate_in_chroma(self.test_dataset.chroma)

        self.test_dataset.user_pool.add_uids([self.test_username])
        self.test_dataset.write_current_user_pool()

        print(self.test_dataset.user_pool.fetch_all_user_objects(loader))


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

        user_loader = entities.EntityLoader(base = entities.BaseLoader(from_sqlite=True))
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        loader = entities.EntityLoader(base=entities.BaseLoader(from_att_dict=True, att_dict=post_dict), derived=HN_entities.HNSubmissionLoader(user_factory, embeddings=True))

        post = self.test_dataset.entity_factory("root", self.insertion_num, loader)
        post.pupdate_in_sqlite(self.test_dataset.sqlite)
        post.pupdate_in_chroma(self.test_dataset.chroma)
        self.test_dataset.sf.add_root(self.insertion_num)
        self.test_dataset.write_current_sf()


    
    """
        Test inserting a comment to a root post.
    """
    def test_comment_insertion_to_root(self):

        comment_dict = {
            "by": self.test_username,
            "id": self.insertion_num + 1,
            "time": int(time.time()),
            "text": "test text"
        }

        user_loader = entities.EntityLoader(base = entities.BaseLoader(from_sqlite=True))
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        loader = entities.EntityLoader(base=entities.BaseLoader(from_att_dict=True, att_dict=comment_dict), derived=HN_entities.HNSubmissionLoader(user_factory, embeddings=True))

        comment = self.test_dataset.entity_factory("branch", self.insertion_num + 1, loader)
        comment.pupdate_in_sqlite(self.test_dataset.sqlite)
        comment.pupdate_in_chroma(self.test_dataset.chroma)
        parent_node = self.test_dataset.sf.get_submission(self.insertion_num)
        parent_node.add_kid(self.insertion_num + 1)
        self.test_dataset.write_current_sf()

        
    """
        Test inserting a comment under an existing comment.
    """
    def test_comment_insertion_to_leaf(self):
        comment_dict = {
            "by": self.test_username,
            "id": self.insertion_num + 2,
            "time": int(time.time()),
            "text": "test text"
        }

        user_loader = entities.EntityLoader(base = entities.BaseLoader(from_sqlite=True))
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        loader = entities.EntityLoader(base=entities.BaseLoader(from_att_dict=True, att_dict=comment_dict), derived=HN_entities.HNSubmissionLoader(user_factory, embeddings=True))

        comment = self.test_dataset.entity_factory("branch", self.insertion_num + 2, loader)
        comment.pupdate_in_sqlite(self.test_dataset.sqlite)
        comment.pupdate_in_chroma(self.test_dataset.chroma)
        parent_node = self.test_dataset.sf.get_submission(self.insertion_num + 1)
        parent_node.add_kid(self.insertion_num + 2)
        self.test_dataset.write_current_sf()

    """
        Test removing a user from the dataset.
    """
    def test_user_removal(self):
        sub_loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True))
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True, embeddings=True), derived=HN_entities.HNUserLoader(post_factory, comment_factory))
        
        new_user = self.test_dataset.entity_factory("user", self.test_username, loader)
        new_user.delete_from_sqlite(self.test_dataset.sqlite)
        new_user.delete_from_chroma(self.test_dataset.chroma)
        self.test_dataset.user_pool.remove_uids([self.test_username])
        self.test_dataset.write_current_user_pool()

        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True, embeddings=False), derived=HN_entities.HNUserLoader(post_factory, comment_factory))
        print(self.test_dataset.user_pool.fetch_all_user_objects(loader))


    """
        Test removing a post from the dataset.
    """
    def test_post_removal(self):
        user_loader = entities.EntityLoader(base = entities.BaseLoader(from_sqlite=True))
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True, embeddings=True), derived=HN_entities.HNSubmissionLoader(user_factory, embeddings=True))

        post = self.test_dataset.entity_factory("root", self.insertion_num, loader)
        
        post.delete_from_sqlite(self.test_dataset.sqlite)
        post.delete_from_chroma(self.test_dataset.chroma)
        self.test_dataset.sf.remove_root(self.insertion_num)
        self.test_dataset.write_current_sf()

    """
        Test removing a comment from the dataset.
    """
    def test_comment_removal_from_leaf(self):
        user_loader = entities.EntityLoader(base = entities.BaseLoader(from_sqlite=True))
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True, embeddings=True), derived=HN_entities.HNSubmissionLoader(user_factory, embeddings=True))

        comment = self.test_dataset.entity_factory("branch", self.insertion_num + 2, loader)
        
        comment.delete_from_sqlite(self.test_dataset.sqlite)
        comment.delete_from_chroma(self.test_dataset.chroma)
        self.test_dataset.sf.remove_submission(self.insertion_num + 2)
        self.test_dataset.write_current_sf()

    def test_comment_removal_from_root(self):
        user_loader = entities.EntityLoader(base = entities.BaseLoader(from_sqlite=True))
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        loader = entities.EntityLoader(base=entities.BaseLoader(from_sqlite=True, embeddings=True), derived=HN_entities.HNSubmissionLoader(user_factory, embeddings=True))

        comment = self.test_dataset.entity_factory("branch", self.insertion_num + 1, loader)
        
        comment.delete_from_sqlite(self.test_dataset.sqlite)
        comment.delete_from_chroma(self.test_dataset.chroma)
        self.test_dataset.sf.remove_submission(self.insertion_num + 1)
        self.test_dataset.write_current_sf()

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
        self.test_comment_removal_from_leaf()
        self.test_comment_removal_from_root()
        self.test_post_removal()
        self.test_user_removal()
    
    """
        Run a full test of all CRUD capabilities.
    """
    def test_full(self):
        self.test_insertion()
        self.test_removal()

if __name__ == '__main__':
    unittest.main()