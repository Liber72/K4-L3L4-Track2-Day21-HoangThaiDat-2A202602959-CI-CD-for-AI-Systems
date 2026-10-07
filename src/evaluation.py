"""Threshold sweep and per-class evaluation for the lab's holdout dataset."""

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score


def sweep_thresholds(target, probabilities):
    probabilities = np.asarray(probabilities)
    if probabilities.ndim != 1 or not np.isfinite(probabilities).all():
        raise ValueError("Expected finite positive-class probabilities")
    if ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Probabilities must be between 0 and 1")
    results = [{"threshold": round(0.1 + 0.05 * index, 2), "f1_score": 0.0}
               for index in range(17)]
    for result in results:
        result["f1_score"] = float(f1_score(
            target, probabilities >= result["threshold"], zero_division=0))
    best = max(results, key=lambda row: (row["f1_score"], -abs(row["threshold"] - 0.5),
                                       -row["threshold"]))
    return best, results


def detailed_report(target, predictions, threshold):
    matrix = confusion_matrix(target, predictions, labels=[0, 1])
    text = (f"Decision threshold: {threshold:.2f}\n"
            "Confusion matrix: rows=actual, columns=predicted; labels=[0, 1]\n"
            f"{matrix}\n\n" + classification_report(
                target, predictions, labels=[0, 1],
                target_names=["thu_nhap_thap (0)", "thu_nhap_cao (1)"],
                digits=4, zero_division=0))
    return matrix.tolist(), text
