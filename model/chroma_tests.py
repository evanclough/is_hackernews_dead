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

        cls.dataset = dataset.Dataset(cls.test_dataset_name, existing_dataset_name="SCRATCH_TEST", embedding_model=cls.test_embedding_model)
        cls.dataset.initialize_for_run()

        cls.insertion_num = 888
        cls.test_username = f"test_username{cls.insertion_num}"


        print(f"Running tests on existing dataset {cls.test_dataset_name}...")
        print(f"test insertion number: {cls.insertion_num}")

    

    

if __name__ == '__main__':
    unittest.main()