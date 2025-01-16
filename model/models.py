"""
Train the when model on a given dataset
"""

import sys

import utils
from classes import Dataset

def when(feature_set):
    model = lambda f: True
    return model(feature_set)

def what(feature_set):
    model = lambda f: "yahooooo!"
    return model(feature_set)

def run_model(dataset, interval, total_duration=None):
    dataset.initialize_for_run()

    if total_duration == None:
        end_time = dataset.get_initial_time() + total_duration
    else:
        #dataset.get_end_time()
        end_time = dataset.get_initial_time() + total_duration

    while(dataset.get_current_time() < end_time):
        current_feature_sets = dataset.get_all_current_feature_sets()
        for feature_set in current_feature_sets:
            if when(feature_set):
                response = what(feature_set)
                #add response to dataset
        dataset.advance_current_time(interval)


def train_model(dataset):
    return -1

if __name__ == "__main__":
    dataset_name = sys.argv[1]
    dataset = Dataset("test_dataset", sqlite_dataset_name=dataset_name)
    run_model(dataset, 60, total_duration=60*60*24)
