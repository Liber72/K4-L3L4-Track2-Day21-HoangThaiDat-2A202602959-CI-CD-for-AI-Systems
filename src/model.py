"""Persist the decision threshold alongside a fitted sklearn classifier."""

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin


class ThresholdClassifier(ClassifierMixin, BaseEstimator):
    def __init__(self, estimator, threshold=0.5):
        self.estimator = estimator
        self.threshold = threshold

    @property
    def feature_names_in_(self):
        return self.estimator.feature_names_in_

    @property
    def classes_(self):
        return self.estimator.classes_

    def fit(self, X, y):
        self.estimator.fit(X, y)
        return self

    def predict_proba(self, X):
        return self.estimator.predict_proba(X)

    def predict(self, X):
        if not np.isfinite(self.threshold) or not 0 <= self.threshold <= 1:
            raise ValueError("Decision threshold must be finite and between 0 and 1")
        positive_index = list(self.classes_).index(1)
        return (self.predict_proba(X)[:, positive_index] >= self.threshold).astype(int)
