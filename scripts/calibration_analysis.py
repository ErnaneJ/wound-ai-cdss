"""
Reproduces the calibration analysis reported in Section IV-B of the paper
(ECE, reliability diagram, Wilson 95% CI for global accuracy), evaluated on
the same 234-image held-out test partition used in `lesion_classifier.ipynb`.

Usage:
    python3 scripts/calibration_analysis.py

Requires the released checkpoint at backend/models/best_wound_classifier_FINETUNED.h5
and the test images at drive/dataset/test/<CLASS>/*.
"""

import json
import os

import numpy as np
from scipy.stats import norm
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import ImageDataGenerator

CLASSES = ["BG", "D", "N", "P", "S", "V"]
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
N_BINS = 10

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINT_PATH = os.path.join(ROOT, "backend", "models", "best_wound_classifier_FINETUNED.h5")
TEST_DIR = os.path.join(ROOT, "drive", "dataset", "test")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_output")


def wilson_confidence_interval(successes, n, confidence=0.95):
    z = norm.ppf(1 - (1 - confidence) / 2)
    p = successes / n
    denominator = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denominator
    margin = (z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2))) / denominator
    return center - margin, center + margin


def expected_calibration_error(confidences, correct, n_bins=N_BINS):
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    n = len(confidences)
    ece = 0.0
    bins = []
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        in_bin = (confidences > lo) & (confidences <= hi) if i > 0 else (confidences >= lo) & (confidences <= hi)
        bin_count = in_bin.sum()
        if bin_count == 0:
            bins.append({"range": (lo, hi), "count": 0, "accuracy": None, "confidence": None})
            continue
        bin_accuracy = correct[in_bin].mean()
        bin_confidence = confidences[in_bin].mean()
        ece += (bin_count / n) * abs(bin_accuracy - bin_confidence)
        bins.append({
            "range": (lo, hi),
            "count": int(bin_count),
            "accuracy": float(bin_accuracy),
            "confidence": float(bin_confidence),
        })
    return ece, bins


def plot_reliability_diagram(bins, out_path):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 5), dpi=200)
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect calibration")

    centers = [(b["range"][0] + b["range"][1]) / 2 for b in bins]
    accuracies = [b["accuracy"] if b["accuracy"] is not None else 0 for b in bins]
    width = 1.0 / len(bins)
    ax.bar(centers, accuracies, width=width * 0.9, edgecolor="black", color="#4C72B0", alpha=0.85, label="Observed accuracy")

    ax.set_xlabel("Confidence")
    ax.set_ylabel("Accuracy")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("Reliability diagram (10 bins)")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    model = load_model(CHECKPOINT_PATH)

    test_datagen = ImageDataGenerator(rescale=1.0 / 255)
    test_generator = test_datagen.flow_from_directory(
        TEST_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        classes=CLASSES,
        shuffle=False,
    )

    probabilities = model.predict(test_generator, verbose=0)
    true_labels = test_generator.classes
    predicted_labels = np.argmax(probabilities, axis=1)
    confidences = np.max(probabilities, axis=1)
    correct = (predicted_labels == true_labels).astype(float)

    n = len(true_labels)
    n_correct = int(correct.sum())
    accuracy = n_correct / n
    ci_low, ci_high = wilson_confidence_interval(n_correct, n)

    ece, bins = expected_calibration_error(confidences, correct)

    results = {
        "n_test_images": n,
        "accuracy": accuracy,
        "wilson_95ci": [ci_low, ci_high],
        "ece": ece,
        "mean_confidence": float(confidences.mean()),
        "bins": bins,
    }

    with open(os.path.join(OUTPUT_DIR, "calibration_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    plot_reliability_diagram(bins, os.path.join(OUTPUT_DIR, "reliability_diagram.png"))

    print(f"n = {n}, accuracy = {accuracy:.4f}, Wilson 95% CI = [{ci_low:.4f}, {ci_high:.4f}]")
    print(f"ECE = {ece:.4f}, mean confidence = {confidences.mean():.4f}")
    print(f"Model is {'underconfident' if confidences.mean() < accuracy else 'overconfident'} on average.")


if __name__ == "__main__":
    main()
