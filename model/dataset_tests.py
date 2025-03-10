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
        base_loader = entities.SqliteLoader("base")
        loader = entities.EntityLoader(base=base_loader)
        self.test_dataset.user_pool.fetch_all_user_objects(loader)

    """
        Test loading hn derived attributes
    """
    def test_derived_upl(self):
        base_loader = entities.SqliteLoader("base")
        sub_loader = entities.EntityLoader(base=base_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        user_derived_loader = HN_entities.HNUserLoader(post_factory, comment_factory)
        loader = entities.EntityLoader(base=base_loader, derived=user_derived_loader)

        self.test_dataset.user_pool.fetch_all_user_objects(loader)

    """
        Test loading base attributes for the submission forest.
    """
    def test_base_sfl(self):
        base_loader = entities.SqliteLoader("base")
        loader = entities.EntityLoader(base=base_loader)
        self.test_dataset.sf.dfs_roots(lambda a: a, loader=loader)

    """
        Test loading hn derived attributes
    """
    def test_derived_sfl(self):
        base_loader = entities.SqliteLoader("base")
        user_loader = entities.EntityLoader(base=base_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        sf_derived_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_loader, derived=sf_derived_loader)
        self.test_dataset.sf.dfs_roots(lambda a: a, loader=loader)


    def test_merged_sfl(self):
        base_loader = entities.SqliteLoader("base")
        loader = entities.EntityLoader(base=base_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        sf_derived_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_loader)
        branches = self.test_dataset.sf.load_all_branches(loader)
        for i in range(10):
            print("TEXT:" + branches[i].get_att("text") + "\nCHAIN: " + branches[i].get_att("full_text_chain"))
            print("\n\n\n")

    """
        Test generating embeddings for the user pool.
    """
    def test_embed_up(self):
        base_loader = entities.SqliteLoader("base")
        sub_loader = entities.EntityLoader(base=base_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        user_derived_loader = HN_entities.HNUserLoader(post_factory, comment_factory)
        loader = entities.EntityLoader(base=base_loader, derived=user_derived_loader)

        user_objects = self.test_dataset.user_pool.fetch_all_user_objects(loader=loader)

        for user in user_objects:
            user.pupdate_in_chroma(embed_sub_his=True)

    def test_embed_sf(self):
        base_loader = entities.SqliteLoader("base")
        root_loader = entities.EntityLoader(base=base_loader)
        branch_loader = entities.EntityLoader(base=base_loader)
        self.test_dataset.sf.embed(root_loader, branch_loader)

    def test_load_up_embeddings(self):
        base_loader = entities.SqliteLoader("base", embeddings=True)
        sub_loader = entities.EntityLoader(base=base_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        derived_loader = HN_entities.HNUserLoader(post_factory, comment_factory, sub_att_classes=['base'], embeddings=True)
        loader = entities.EntityLoader(base=base_loader, derived=derived_loader)

        user_objects = self.test_dataset.user_pool.fetch_all_user_objects(loader=loader)

        for user in user_objects:
            print(user.embeddings)
            for comment in user.get_att("comments"):
                print(comment.embeddings)


    def test_load_sf_embeddings(self):
        base_loader = entities.SqliteLoader("base", embeddings=True)
        root_loader = entities.EntityLoader(base=base_loader)
        branch_loader = entities.EntityLoader(base=base_loader)
        loaded_sf = self.test_dataset.sf.load_dict_list(root_loader, branch_loader, embeddings=True)
        for root in loaded_sf:
            print(root['root'].embeddings)
            for branch in root['branches']:
                print(branch.embeddings)


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
        base_sqlite_loader = entities.SqliteLoader("base")
        sub_loader = entities.EntityLoader(base=base_sqlite_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        base_user_loader = entities.DictLoader("base", user_dict)
        derived_user_loader  =HN_entities.HNUserLoader(post_factory, comment_factory)
        loader = entities.EntityLoader(base=base_user_loader, derived=derived_user_loader)
        new_user = self.test_dataset.entity_factory("user", self.test_username, loader)
        new_user.pupdate_in_sqlite()
        new_user.pupdate_in_chroma()

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

        base_sqlite_loader = entities.SqliteLoader("base")

        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        base_post_loader = entities.DictLoader("base", post_dict)
        derived_post_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_post_loader, derived=derived_post_loader)
        post = self.test_dataset.entity_factory("root", self.insertion_num, loader)

        post.pupdate_in_sqlite()
        post.add_to_author_history()
        post.pupdate_in_chroma()

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

        base_sqlite_loader = entities.SqliteLoader("base")

        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        base_comment_loader = entities.DictLoader("base", comment_dict)
        derived_comment_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_comment_loader, derived=derived_comment_loader)
        comment = self.test_dataset.entity_factory("branch", self.insertion_num + 1, loader)

        comment.pupdate_in_sqlite()
        comment.add_to_author_history()
        comment.pupdate_in_chroma()

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

        base_sqlite_loader = entities.SqliteLoader("base")

        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        base_comment_loader = entities.DictLoader("base", comment_dict)
        derived_comment_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_comment_loader, derived=derived_comment_loader)
        comment = self.test_dataset.entity_factory("branch", self.insertion_num + 2, loader)

        comment.pupdate_in_sqlite()
        comment.add_to_author_history()
        comment.pupdate_in_chroma()

        parent_node = self.test_dataset.sf.get_submission(self.insertion_num + 1)
        parent_node.add_kid(self.insertion_num + 2)        
        self.test_dataset.write_current_sf()

    """
        Test removing a user from the dataset.
    """
    def test_user_removal(self):

        
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)
        sub_loader = entities.EntityLoader(base=base_sqlite_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("branch", id_val, sub_loader)
        derived_user_loader =HN_entities.HNUserLoader(post_factory, comment_factory)
        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_user_loader)
        new_user = self.test_dataset.entity_factory("user", self.test_username, loader)


        new_user.delete_from_sqlite()
        new_user.delete_from_chroma()

        self.test_dataset.user_pool.remove_uids([self.test_username])
        self.test_dataset.write_current_user_pool()

        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_user_loader)
        print(self.test_dataset.user_pool.fetch_all_user_objects(loader))


    """
        Test removing a post from the dataset.
    """
    def test_post_removal(self):
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)

        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        derived_post_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_post_loader)
        post = self.test_dataset.entity_factory("root", self.insertion_num, loader)
        
        post.delete_from_sqlite()
        post.remove_from_author_history()


        post.delete_from_chroma()
        self.test_dataset.sf.remove_root(self.insertion_num)
        self.test_dataset.write_current_sf()

    """
        Test removing a comment from the dataset.
    """
    def test_comment_removal_from_leaf(self):
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)

        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        derived_comment_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_comment_loader)
        comment = self.test_dataset.entity_factory("branch", self.insertion_num + 2, loader)

        
        comment.delete_from_sqlite()
        comment.remove_from_author_history()

        comment.delete_from_chroma()
        self.test_dataset.sf.remove_submission(self.insertion_num + 2)
        self.test_dataset.write_current_sf()

    def test_comment_removal_from_root(self):
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)

        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        derived_comment_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_comment_loader)
        comment = self.test_dataset.entity_factory("branch", self.insertion_num + 1, loader)
        
        comment.delete_from_sqlite()
        comment.remove_from_author_history()

        comment.delete_from_chroma()
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

class GenTests(unittest.TestCase):

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
        cls.post_test_num = 41848209

        print(f"Running sqlite tests on existing dataset {cls.test_dataset_name}...")
        print(f"test insertion number: {cls.insertion_num}")

    def test_basic(self):
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)

        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)

        derived_post_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_post_loader)
        post = self.test_dataset.entity_factory("root", self.insertion_num, loader)

        post.generate_attribute("url_content_summary", self.test_dataset.llm)
        post.pupdate_in_sqlite()
        post.pupdate_in_chroma()

        gen_sqlite_loader = entities.SqliteLoader("generated", embeddings=True)

        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_post_loader, generated=gen_sqlite_loader)

        post = self.test_dataset.entity_factory("root", self.insertion_num, loader)
        print(post.get_att_dict())

    def test_llm_cost_estimate(self):
        self.test_dataset.llm.estimate_prompt_cost("TEST581985715981752", "ADSKJALKJALSFKJFA", accrue=True)
        self.test_dataset.llm.estimate_prompt_cost("TEST581985715981752", "ADSKJALKJALSFKJFA", accrue=True)
        self.test_dataset.llm.print_accrued_costs()

        self.test_dataset.llm.estimate_prompt_cost("TEST581985715981752", "ADSKJALKJALSFKJFA", accrue=True)
        self.test_dataset.llm.estimate_prompt_cost("TEST581985715981752", "ADSKJALKJALSFKJFA", accrue=True)
        self.test_dataset.llm.estimate_prompt_cost("TEST581985715981752", "ADSKJALKJALSFKJFA", accrue=True)
        self.test_dataset.llm.print_accrued_costs()

    def test_EM_cost_estimate(self):
        self.test_dataset.embedding_model.estimate_doc_cost("TEST581985715981752", accrue=True)

        self.test_dataset.embedding_model.print_accrued_costs()

class WhenTests(unittest.TestCase):
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

    def test_basic(self):
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)

        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        derived_post_loader = HN_entities.HNSubmissionLoader(user_factory)

        gen_sqlite_loader = entities.SqliteLoader("generated", embeddings=True)

        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_post_loader, generated=gen_sqlite_loader)

        post = self.test_dataset.entity_factory("root", self.insertion_num, loader)

        print(post.get_numpy_array())

if __name__ == '__main__':
    unittest.main()