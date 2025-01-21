"""
Train the when model on a given dataset
"""

import sys

import utils
import dataset

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

if __name__ == "__main__":
    dataset_name = sys.argv[1]
    dataset = dataset.Dataset("test_dataset", existing_dataset_name=dataset_name)
    dataset.initialize_for_run()
    dataset.get_all_current_feature_sets()
    run_model(dataset, 60, total_duration=60*60*24)
