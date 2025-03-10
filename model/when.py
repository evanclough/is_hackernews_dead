import utils
import entities

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_curve, auc
from sklearn.preprocessing import StandardScaler


class When:
    def __init__(self, name, entity_models, check_if_responded, combined_features=[]):
        self.name = name
        self.model_dir_path = utils.fetch_env_var("ROOT_WHEN_MODELS_DIR")
        self.entity_models = entity_models
        self.check_if_responded = check_if_responded
        self.combined_features = []
        
    def __str__(self):
        return f"When Model: {self.name}"

    def get_columns(self):
        columns = []

        for entity_type, entity_model in self.entity_models.items():
            for att_class in entity_model['attributes']:
                for att_model in att_class:
                    if att_model['include_when']
                        col_name = f"{entity_type}_{att_model['name']}"
                        if att_model['embed']:
                            columns = self.columns + [f"{col_name}_{i}" for i in range(self.dataset.embedding_model.dimension)]
                        else:
                            columns.append(col_name)

        columns = columns + [feature_name for feature_name in self.combined_features.keys()]

        return columns

    def get_feature_row(self, user, root, branch):
        user_np_arr = user.get_numpy_array()
        root_np_arr = root.get_numpy_array()
        branch_np_arr = branch.get_numpy_array()
        combined_np_arr = np.array([f(user, root, branch) for f in self.combined_features.values()])

        return np.concatenate((user_np_arr, root_np_arr, branch_np_arr, combined_np_arr))

    def load_dataset(self, dataset, loaders):
        self.user_index = 0
        self.root_index = 0
        self.branch_index = 0
        self.dataset = dataset
        self.loaders = loaders

        self.columns = []
        for entity_type, entity_model in self.entity_models.items():
            for att_class in entity_model['attributes']:
                for att_model in att_class:
                    if att_model['include_when']
                        col_name = f"{entity_type}_{att_model['name']}"
                        if att_model['embed']:
                            columns = self.columns + [f"{col_name}_{i}" for i in range(self.dataset.embedding_model.dimension)]
                        else:
                            columns.append(col_name)

    def get_batch(self, batch_size):
        feature_rows = []
        label_rows = []

        batch_index = 0

        for user_index in range(self.user_index, len(self.dataset.user_pool.uids)):

            user_object = self.dataset.user_pool.entity_factory("user", self.dataset.user_pool.uids[user_index] self.loaders['user'])

            for root_index in range(self.root_index, len(self.dataset.sf.roots)):

                root = self.sf.roots[root_index]
                root_object = root.fetch_submission_object(self.loaders['root'])
    
                branches = root.load_branches(self.loaders['branch'], embeddings=True)
                for branch_index in range(self.branch_index, len(branches)):
                    branch = branches[branch_index]

                    feature_row = self.get_feature_row(user_object, root_object, branch_object)
                    feature_rows.append(row)

                    label_row = np.array([int(self.check_if_responded(user_object, branch_object))])
                    label_rows.append(label_row)

                    if batch_index == batch_size:
                        return pd.DataFrame(feature_rows, columns=columns), pd.DataFrame(label_rows, columns=['responded?'])

        return (feature_rows, label_rows)


def XGBoostWhen(When):

    def init_model(self):
        self.path = self.model_dir_path + name + ".json"

        if utils.check_file_exists(self.path):
            self.model = xgb.XGBClassifier()
            self.model.load(self.path)
        else:
            self.model = xgb.XGBClassifier(
                scale_pos_weight=scale_pos_weight,
                learning_rate=0.1,
                n_estimators=100,
                max_depth=4,
                min_child_weight=1,
                gamma=0,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='binary:logistic',
                eval_metric='auc',
                random_state=42
            )

    def save(self):
        self.model.save_model(self.path)

    def train(self, dataset, batch_size):
        input_data = []
