"""
    General unit tests for the dataset class.
"""

import numpy as np

import unittest
import time
import json

import utils
import dataset
import HN_entities
import entities
import when

class NewTests(unittest.TestCase):
    @classmethod
    def setupClass(cls):
        cls.forum = entities.Forum(HN_entities.HNUser, HN_entities.HNPost, HN_entities.HNComment)
        cls.test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
        cls.test_dataset = dataset.Dataset(cls.test_dataset_name, cls.forum)

    

"""
    Tests for initializing the dataset with various options.
"""
class InitTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.entity_classes = {
            "user": HN_entities.HNUser,
            "root": HN_entities.HNPost,
            "stem": HN_entities.HNComment
        }
        cls.test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
        cls.test_dataset = dataset.Dataset(cls.test_dataset_name, cls.entity_classes)


        print(f"Running tests on dataset {cls.test_dataset_name}...")

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
        comment_factory = lambda id_val: self.test_dataset.entity_factory("stem", id_val, sub_loader)
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
        sf_derived_loader = HN_entities.HNSubmissionLoader(user_factory=user_factory)
        loader = entities.EntityLoader(base=base_loader, derived=sf_derived_loader)
        self.test_dataset.sf.dfs_roots(lambda a: a, loader=loader)


    """
        Test generating embeddings for the user pool.
    """
    def test_embed_up(self):
        base_loader = entities.SqliteLoader("base")
        gen_loader = entities.SqliteLoader("generated")
        der_loader= HN_entities.HNSubmissionLoader()
        sub_loader = entities.EntityLoader(base=base_loader, derived=der_loader, generated = gen_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("stem", id_val, sub_loader)
        user_derived_loader = HN_entities.HNUserLoader(post_factory, comment_factory)
        loader = entities.EntityLoader(base=base_loader, derived=user_derived_loader)

        for user in self.test_dataset.user_pool.iterate(loader):
            user.pupdate_in_chroma(embed_sub_his=True)

    def test_embed_sf(self):
        base_loader = entities.SqliteLoader("base")
        gen_loader = entities.SqliteLoader("generated")

        user_loader = entities.EntityLoader(base=base_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        derived_loader = HN_entities.HNSubmissionLoader()
        
        loader = entities.EntityLoader(base=base_loader, derived=derived_loader, generated=gen_loader)

        for node in self.test_dataset.sf.iter_dfs(loader):
            node.pupdate_in_chroma(embed_author=True)
        

    def test_load_up_embeddings(self):
        base_loader = entities.SqliteLoader("base", embeddings=True)
        gen_loader = entities.SqliteLoader('generated', embeddings=True)
        user_loader = entities.EntityLoader(base=base_loader)
        derived_loader = HN_entities.HNSubmissionLoader(embeddings=True, author_att_classes=[])
        sub_loader = entities.EntityLoader(base=base_loader, derived=derived_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("stem", id_val, sub_loader)
        derived_loader = HN_entities.HNUserLoader(post_factory, comment_factory, sub_att_classes=['base'], embeddings=True)
        loader = entities.EntityLoader(base=base_loader, derived=derived_loader,generated=gen_loader)

        for user in self.test_dataset.user_pool.iterate(loader):
            print(user.embeddings)
            for post in user.get_att("posts"):
                print(post.embeddings)
            for comment in user.get_att("comments"):
                print(comment.embeddings)
            for fav in user.get_att("favorite_posts"):
                print(fav.embeddings)


    def test_load_sf_embeddings(self):
        base_loader = entities.SqliteLoader("base", embeddings=True)
        gen_loader = entities.SqliteLoader("generated", embeddings=True)

        user_loader = entities.EntityLoader(base=base_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        derived_loader = HN_entities.HNSubmissionLoader(user_factory=user_factory, embeddings=True, author_att_classes=['base', 'derived', 'generated'])
        
        loader = entities.EntityLoader(base=base_loader, derived=derived_loader, generated=gen_loader)

        for node in self.test_dataset.sf.iter_dfs(loader):
            print(node.embeddings)
            print(node.get_att("author").embeddings)


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
            "stem": HN_entities.HNComment
        }
        cls.test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
        cls.test_dataset = dataset.Dataset(cls.test_dataset_name, cls.entity_classes, verbose=True)
        cls.insertion_num = 33333
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
        comment_factory = lambda id_val: self.test_dataset.entity_factory("stem", id_val, sub_loader)
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
        comment = self.test_dataset.entity_factory("stem", self.insertion_num + 1, loader)

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
        comment = self.test_dataset.entity_factory("stem", self.insertion_num + 2, loader)

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
        comment_factory = lambda id_val: self.test_dataset.entity_factory("stem", id_val, sub_loader)
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
        comment = self.test_dataset.entity_factory("stem", self.insertion_num + 2, loader)

        
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
        comment = self.test_dataset.entity_factory("stem", self.insertion_num + 1, loader)
        
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

class IterableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entity_classes = {
            "user": HN_entities.HNUser,
            "root": HN_entities.HNPost,
            "stem": HN_entities.HNComment
        }
        cls.test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
        cls.test_dataset = dataset.Dataset(cls.test_dataset_name, cls.entity_classes)
        cls.insertion_num = 33333
        cls.test_username = f"test_username{cls.insertion_num}"

        print(f"Running sqlite tests on existing dataset {cls.test_dataset_name}...")
        print(f"test insertion number: {cls.insertion_num}")

    def test_up(self):
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)
        sub_loader = entities.EntityLoader(base=base_sqlite_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("stem", id_val, sub_loader)
        derived_user_loader =HN_entities.HNUserLoader(post_factory, comment_factory)
        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_user_loader)

        for user in self.test_dataset.user_pool.iterate(loader):
            print(user.get_att("username"))

    def test_sf(self):
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)
        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        derived_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_loader)

        print("DFS:")
        for submission in self.test_dataset.sf.iter_dfs(loader):
            print(submission.get_att("id"))

        print("BFS: ")
        for submission in self.test_dataset.sf.iter_bfs(loader):
            print(submission.get_att("id"))

    def test_sf_branch(self):
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)
        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        derived_loader = HN_entities.HNSubmissionLoader(user_factory)
        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_loader)

        sf_iterable = self.test_dataset.sf.iter_dfs_branches(loader)

        for branch in sf_iterable:
            print("BRANCH")
            print(f"ROOT: {branch.root.get_att('id')}")
            print("STEMS: ")
            for stem in branch.stems:
                print(stem.get_att("id"))
            print()


class GenTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.entity_classes = {
            "user": HN_entities.HNUser,
            "root": HN_entities.HNPost,
            "stem": HN_entities.HNComment
        }
        cls.test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
        cls.test_dataset = dataset.Dataset(cls.test_dataset_name, cls.entity_classes)
        cls.insertion_num = 55555
        cls.test_username = f"test_username{cls.insertion_num}"
        cls.post_test_num = 41848209

        print(f"Running sqlite tests on existing dataset {cls.test_dataset_name}...")
        print(f"test insertion number: {cls.insertion_num}")

    def test_sf_gen(self):
        base_sqlite_loader = entities.SqliteLoader("base", embeddings=True)
        user_loader = entities.EntityLoader(base=base_sqlite_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        loader = entities.EntityLoader(base=base_sqlite_loader)

        #for root in self.test_dataset.sf.iter_roots(loader):
        #    root.generate_attribute("url_content_summary", self.test_dataset.llm)
        #    root.pupdate_in_sqlite()
        #    root.pupdate_in_chroma()

        gen_loader = entities.SqliteLoader("generated", embeddings=True)
        derived_loader = HN_entities.HNSubmissionLoader(user_factory)

        loader = entities.EntityLoader(base=base_sqlite_loader, derived=derived_loader, generated=gen_loader)

        for root in self.test_dataset.sf.iter_roots(loader):
            print(root.get_att_dict())


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
            "stem": HN_entities.HNComment
        }
        cls.test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
        cls.test_dataset = dataset.Dataset(cls.test_dataset_name, cls.entity_classes)
        cls.insertion_num = 55555
        cls.test_username = f"test_username{cls.insertion_num}"

        print(f"Running sqlite tests on existing dataset {cls.test_dataset_name}...")
        print(f"test insertion number: {cls.insertion_num}")

    def test_basic(self):
        base_loader = entities.SqliteLoader("base", embeddings=True)
        gen_loader = entities.SqliteLoader('generated', embeddings=True)
        user_loader = entities.EntityLoader(base=base_loader)
        derived_loader = HN_entities.HNSubmissionLoader(embeddings=True, author_att_classes=[])
        sub_loader = entities.EntityLoader(base=base_loader, derived=derived_loader, generated=gen_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("stem", id_val, sub_loader)
        derived_loader = HN_entities.HNUserLoader(post_factory, comment_factory, sub_att_classes=['base', 'generated'], embeddings=True)

        user_loader = entities.EntityLoader(base=base_loader, derived=derived_loader,generated=gen_loader)


        user_loader = entities.EntityLoader(base=base_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        derived_loader = HN_entities.HNSubmissionLoader(user_factory=user_factory, embeddings=True, author_att_classes=['base', 'derived', 'generated'])
        
        branch_loader = entities.EntityLoader(base=base_loader, derived=derived_loader, generated=gen_loader)

        def get_training_row(user, branch, start_time, stop_time):
            user_features = np.array([user.get_att("karma"), user.get_att("created")])
            user_features = np.concatenate((user_features, user.embeddings['about']))

            root = branch.root
            root_features = np.array([root.get_att("score"), root.get_att("time")])
            root_features = np.concatenate((root_features, root.embeddings['full_content']))

            latest_time = 0
            average_time = 0
            stem_embedding_average = np.zeros(self.test_dataset.embedding_model.dimension)
            stems = branch.stems[:-1]
            for stem in stems:
                stem_embedding_average = stem_embedding_average +  (1 / len(stems)) * stem.embeddings['text']
                latest_time = stem.get_time()
                average_time += stem.get_time() * (1 / (len(stems)))
            
            stem_features = np.array([latest_time, average_time])
            stem_features = np.concatenate((stem_features, stem_embedding_average))

            features = np.concatenate((user_features, root_features, stem_features, np.array([start_time])))

            latest_stem = branch.stems[-1]

            label = int(latest_stem.get_time() > start_time and latest_stem.get_time() < stop_time)
            return features, label

        def get_inference_row(user, branch, time):
            user_features = np.array([user.get_att("karma"), user.get_att("created")])
            user_features = np.concatenate((user_features, user.embeddings['about']))

            root = branch.root
            root_features = np.array([root.get_att("score"), root.get_att("time")])
            root_features = np.concatenate((root_features, root.embeddings['full_content']))

            latest_time = 0
            average_time = 0
            stem_embedding_average = np.zeros(self.test_dataset.embedding_model.dimension)
            stems = branch.stems
            for stem in stems:
                stem_embedding_average = stem_embedding_average +  (1 / len(stems)) * stem.embeddings['text']
                latest_time = stem.get_time()
                average_time += stem.get_time() * (1 / (len(stems)))

            stem_features = np.array([latest_time, average_time])
            stem_features = np.concatenate((stem_features, stem_embedding_average))

            features = np.concatenate((user_features, root_features, stem_features, np.array([time])))

            return features


        model = when.When("test", get_training_row, lambda a: a)

        model.save_ds_train_data(self.test_dataset, user_loader, branch_loader)

    def test_export_npy(self):
        base_loader = entities.SqliteLoader("base", embeddings=True)
        gen_loader = entities.SqliteLoader('generated', embeddings=True)
        user_loader = entities.EntityLoader(base=base_loader)
        derived_loader = HN_entities.HNSubmissionLoader(embeddings=True, author_att_classes=[])
        sub_loader = entities.EntityLoader(base=base_loader, derived=derived_loader, generated=gen_loader)
        post_factory = lambda id_val: self.test_dataset.entity_factory("root", id_val, sub_loader)
        comment_factory = lambda id_val: self.test_dataset.entity_factory("stem", id_val, sub_loader)
        derived_loader = HN_entities.HNUserLoader(post_factory, comment_factory, sub_att_classes=['base', 'generated'], embeddings=True)

        user_loader = entities.EntityLoader(base=base_loader, derived=derived_loader,generated=gen_loader)


        user_loader = entities.EntityLoader(base=base_loader)
        user_factory = lambda uid: self.test_dataset.entity_factory("user", uid, user_loader)
        derived_loader = HN_entities.HNSubmissionLoader(user_factory=user_factory, embeddings=True, author_att_classes=['base', 'derived', 'generated'])
        
        branch_loader = entities.EntityLoader(base=base_loader, derived=derived_loader, generated=gen_loader)

        self.test_dataset.export_train_when(user_loader, branch_loader)

    def test_xgboost(self):
        features, labels = self.test_dataset.load_train_when()

        model = when.XGBoostWhen("test2")

        model.init_model()
        model.train(features, labels)


if __name__ == '__main__':
    unittest.main()