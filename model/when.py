import utils
import entities

import numpy as np
import pandas as pd
import xgboost as xgb
import pickle
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_curve, auc
from sklearn.preprocessing import StandardScaler




class When:
    def __init__(self, name):
        self.name = name
        self.model_dir_path = utils.fetch_env_var("ROOT_WHEN_MODELS_DIR")
        self.dir_path = self.model_dir_path + self.name + "/"
        if not utils.check_directory_exists(self.dir_path):
            utils.create_directory(self.dir_path)
        
    def __str__(self):
        return f"When Model: {self.name}"

class XGBoostWhen(When):

    def init_model(self):
        self.path = self.dir_path + self.name + ".pkl"

        self.existing_model = utils.check_file_exists(self.path)

        if self.existing_model:
            with open(self.path, 'rb') as f:
                self.model = pickle.load(f)

    def train(self, features, labels):

        print(features.shape)
        print(labels.shape)

        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42, stratify=labels
        )

        scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

        if not self.existing_model:
            self.model = xgb.XGBClassifier(
                scale_pos_weight=scale_pos_weight,
                learning_rate=0.1,
                n_estimators=50,
                max_depth=5,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='binary:logistic',
                eval_metric='auc',
                random_state=42
            )
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
            xgb_model=self.model if self.existing_model else None
        )
        
        y_pred = self.model.predict(X_test)

        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))

    def save(self):
        with open(self.path, 'wb') as f:
            pickle.dump(self.model, f)
        print(f"model saved to {self.path}")

    def inference(self, feature_set):
        feature_set = np.array([feature_set])
        y_pred = self.model.predict(feature_set)
        y_pred_proba = self.model.predict_proba(feature_set)[:, 1]
        return y_pred, y_pred_proba