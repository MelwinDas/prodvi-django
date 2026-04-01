"""
train.py
--------
Trains two models and saves them as .pt bundles:
  - question_classifier.pt   : classifies a peer review question → category label
  - answer_classifier.pt     : classifies a peer review answer   → sentiment/rating label

Each .pt file stores:
    {
        "encoder_name": str,          # SentenceTransformer model name (re-loaded at inference)
        "svc":          bytes,        # joblib-serialised SVC classifier head
        "label_classes": List[str],   # ordered class names
        "columns": List[str],         # (answer model only) valid category columns
        "metrics": dict               # accuracy, f1, per-class report from CV
    }

Usage:
    python train.py \
        --question-csv  data/prodvi-random-questionset.csv \
        --answer-csv    data/prodvi-dataset-new4.csv \
        --output-dir    models/

Requirements:
    pip install sentence-transformers scikit-learn pandas torch joblib
"""

import argparse
import io
import json
import re
import string
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENCODER_NAME = "all-MiniLM-L6-v2"   # 384-dim, ~80 MB, fast CPU inference

# These must match the column names in prodvi-dataset-new4.csv exactly
ANSWER_COLUMNS = [
    "Ease_of_Working_Together",
    "Cooperation",
    "Work_Ethics",
    "Areas_to_Improve",
    "Helps_Others",
    "Punctuality",
    "Work_Efficiency",
    "Problem_Solving",
    "Adaptability",
    "Communication",
    "Innovation",
    "Leadership",
    "Self_Motivation",
    "Emotional_Intelligence",
]


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def _basic_clean(text: str) -> str:
    """
    Lightweight cleaning that works well before sentence-transformer encoding.
    We intentionally keep stopwords — the transformer handles semantics better
    with full sentences than with stopword-stripped fragments.
    """
    text = str(text).strip().lower()
    # collapse whitespace
    text = re.sub(r"\s+", " ", text)
    # remove non-ascii punctuation that adds noise (keep apostrophes for contractions)
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def preprocess_series(series: pd.Series) -> list[str]:
    return [_basic_clean(t) for t in series.tolist()]


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def encode(encoder: SentenceTransformer, texts: list[str]) -> np.ndarray:
    """Encode a list of texts; show a progress bar for large batches."""
    return encoder.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # cosine-friendly unit vectors
    )


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------

def train_svc(X: np.ndarray, y: np.ndarray, n_folds: int = 5) -> CalibratedClassifierCV:
    """
    Train a calibrated SVC head.
    CalibratedClassifierCV wraps LinearSVC so we get .predict_proba()
    (LinearSVC alone has no probability output).
    n_folds is passed through so calibration never exceeds the smallest class size.
    """
    base = LinearSVC(C=1.0, max_iter=2000, dual=False)
    model = CalibratedClassifierCV(base, cv=n_folds, method="isotonic")
    model.fit(X, y)
    return model


def evaluate(model, X: np.ndarray, y: np.ndarray, label_names: list[str]) -> dict:
    """5-fold stratified CV for honest generalisation estimate."""
    print("  Running 5-fold stratified cross-validation …")
    base = LinearSVC(C=1.0, max_iter=2000, dual=False)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_pred = cross_val_predict(base, X, y, cv=cv)

    f1 = f1_score(y, y_pred, average="weighted")
    report = classification_report(y, y_pred, target_names=label_names, output_dict=True)
    print(f"  Weighted F1 (CV): {f1:.4f}")
    return {"weighted_f1": float(f1), "classification_report": report}


def serialise_svc(model: CalibratedClassifierCV) -> bytes:
    """Serialise the fitted SVC head to bytes using joblib."""
    buf = io.BytesIO()
    joblib.dump(model, buf)
    return buf.getvalue()


def save_pt(path: Path, payload: dict) -> None:
    torch.save(payload, path)
    size_mb = path.stat().st_size / 1e6
    print(f"  Saved → {path}  ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# Question classifier
# ---------------------------------------------------------------------------

def train_question_classifier(
    csv_path: Path,
    encoder: SentenceTransformer,
    output_dir: Path,
) -> None:
    print("\n═══════════════════════════════════════════")
    print(" QUESTION CLASSIFIER")
    print("═══════════════════════════════════════════")

    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} rows from {csv_path.name}")
    print(f"  Columns: {df.columns.tolist()}")

    # Normalise label column (strip parentheses from old format if present)
    df["Label"] = (
        df["Label"]
        .astype(str)
        .str.replace(r"[()]", "", regex=True)
        .str.strip()
    )

    # Drop nulls
    df = df.dropna(subset=["Question", "Label"])
    print(f"  After dropna: {len(df)} rows")
    print(f"  Classes: {sorted(df['Label'].unique())}")

    texts = preprocess_series(df["Question"])

    # Encode
    print("  Encoding questions …")
    X = encode(encoder, texts)

    # Encode labels to integers for sklearn
    le = LabelEncoder()
    y = le.fit_transform(df["Label"].tolist())
    label_names = list(le.classes_)

    # Evaluate (CV) then train final model on full data
    metrics = evaluate(None, X, y, label_names)   # CV uses base LinearSVC internally
    # Re-run evaluate properly:
    base = LinearSVC(C=1.0, max_iter=2000, dual=False)
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_pred_cv = cross_val_predict(base, X, y, cv=cv)
    from sklearn.metrics import f1_score, classification_report
    f1 = f1_score(y, y_pred_cv, average="weighted")
    report = classification_report(y, y_pred_cv, target_names=label_names, output_dict=True)
    metrics = {"weighted_f1": float(f1), "classification_report": report}
    print(f"  Weighted F1 (CV): {f1:.4f}")

    print("  Training final model on full dataset …")
    final_model = train_svc(X, y)

    payload = {
        "model_type": "question_classifier",
        "encoder_name": ENCODER_NAME,
        "svc": serialise_svc(final_model),
        "label_classes": label_names,           # index → human label
        "metrics": metrics,
    }

    save_pt(output_dir / "question_classifier.pt", payload)


# ---------------------------------------------------------------------------
# Answer classifier
# ---------------------------------------------------------------------------

# Normalise dirty / duplicate labels visible in the data.
# Key   = raw label as it appears in the CSV (case-sensitive)
# Value = canonical label to use instead
LABEL_NORMALIZATION: dict[str, str] = {
    # casing duplicates
    "Time management":   "Time Management",
    "Technical skills":  "Technical Skills",
    "often":             "Often",
    # semantic duplicates (keep the more descriptive form)
    "Teamwork":          "Team Collaboration",
}

# Drop any label whose total sample count across all columns is below this.
# CalibratedClassifierCV with cv=5 needs at least 5 samples per class.
MIN_SAMPLES_PER_LABEL = 5


def _normalize_label(label: str) -> str:
    return LABEL_NORMALIZATION.get(label.strip(), label.strip())


def _parse_answer_column(series: pd.Series) -> tuple[list[str], list[str]]:
    """
    Each cell in prodvi-dataset-new4.csv looks like:
        "She communicates clearly with the team(Positive)"
    Split on the last '(' to get text and label.
    """
    texts, labels = [], []
    for raw in series.dropna():
        raw = str(raw).strip()
        if "(" not in raw:
            continue
        idx = raw.rfind("(")
        text = raw[:idx].strip()
        label = raw[idx:].replace("(", "").replace(")", "").strip()
        if text and label:
            texts.append(text)
            labels.append(_normalize_label(label))
    return texts, labels


def train_answer_classifier(
    csv_path: Path,
    encoder: SentenceTransformer,
    output_dir: Path,
) -> None:
    print("\n═══════════════════════════════════════════")
    print(" ANSWER CLASSIFIER")
    print("═══════════════════════════════════════════")

    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} rows from {csv_path.name}")

    # Collect all (text, label) pairs across every answer column
    all_texts, all_labels, all_cols = [], [], []
    for col in ANSWER_COLUMNS:
        if col not in df.columns:
            print(f"  [WARN] Column '{col}' not found — skipping")
            continue
        texts, labels = _parse_answer_column(df[col])
        all_texts.extend(texts)
        all_labels.extend(labels)
        all_cols.append(col)
        print(f"  {col}: {len(texts)} samples")

    print(f"\n  Total samples (before filtering): {len(all_texts)}")

    # Filter out labels with too few samples for cross-validation
    from collections import Counter
    label_counts = Counter(all_labels)
    print(f"\n  Label distribution (after normalization):")
    dropped_labels = set()
    for lbl, cnt in sorted(label_counts.items()):
        flag = f"  ← DROPPING (only {cnt} sample{'s' if cnt > 1 else ''})" if cnt < MIN_SAMPLES_PER_LABEL else ""
        print(f"    {lbl}: {cnt}{flag}")
        if cnt < MIN_SAMPLES_PER_LABEL:
            dropped_labels.add(lbl)

    if dropped_labels:
        print(f"\n  Dropping {len(dropped_labels)} rare label(s): {sorted(dropped_labels)}")
        pairs = [(t, l) for t, l in zip(all_texts, all_labels) if l not in dropped_labels]
        all_texts, all_labels = zip(*pairs)
        all_texts, all_labels = list(all_texts), list(all_labels)

    print(f"  Total samples (after filtering): {len(all_texts)}")

    # Preprocess
    clean_texts = preprocess_series(pd.Series(all_texts))

    # Encode
    print("\n  Encoding answers …")
    X = encode(encoder, clean_texts)

    # Label encode
    le = LabelEncoder()
    y = le.fit_transform(all_labels)
    label_names = list(le.classes_)

    # Dynamically pick n_folds = min(5, smallest class count)
    # so we never ask for more folds than samples in any class
    min_class_count = min(Counter(all_labels).values())
    n_folds = min(5, min_class_count)
    print(f"\n  Using {n_folds}-fold CV (smallest class has {min_class_count} samples)")

    base = LinearSVC(C=1.0, max_iter=2000, dual=False)
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    y_pred_cv = cross_val_predict(base, X, y, cv=cv)
    from sklearn.metrics import f1_score, classification_report
    f1 = f1_score(y, y_pred_cv, average="weighted")
    report = classification_report(y, y_pred_cv, target_names=label_names, output_dict=True)
    metrics = {"weighted_f1": float(f1), "classification_report": report}
    print(f"  Weighted F1 (CV): {f1:.4f}")

    # Train final model — pass n_folds so calibration matches CV
    print("  Training final model on full dataset …")
    final_model = train_svc(X, y, n_folds=n_folds)

    payload = {
        "model_type": "answer_classifier",
        "encoder_name": ENCODER_NAME,
        "svc": serialise_svc(final_model),
        "label_classes": label_names,
        "columns": all_cols,              # saved for reference / validation at inference
        "metrics": metrics,
    }

    save_pt(output_dir / "answer_classifier.pt", payload)


# ---------------------------------------------------------------------------
# Inference helpers  (import these in genprocess.py / qpsvc.py)
# ---------------------------------------------------------------------------

class ModelBundle:
    """
    Thin wrapper around a loaded .pt bundle.
    Use this in genprocess.py and qpsvc.py to replace the old pipeline.

    Example:
        bundle = ModelBundle.load("models/answer_classifier.pt")
        label, confidence = bundle.predict("She communicates very well")
    """

    def __init__(self, payload: dict):
        self.model_type   = payload["model_type"]
        self.encoder_name = payload["encoder_name"]
        self.label_classes = payload["label_classes"]
        self.metrics       = payload.get("metrics", {})
        self.columns       = payload.get("columns", [])

        # Import locally to avoid module startup issues
        import joblib
        
        # We assume the user means "don't load sentence_transformers at all if not used",
        # but the inference currently needs it. So we load it ONLY when a ModelBundle is instantiated.
        try:
            from sentence_transformers import SentenceTransformer
            # Load encoder (cached after first load by sentence-transformers)
            self.encoder = SentenceTransformer(self.encoder_name)
        except ImportError:
            # If the user literally removed it, we'll cleanly handle the fact it's missing
            self.encoder = None

        # Deserialise SVC head from bytes
        buf = io.BytesIO(payload["svc"])
        self.svc = joblib.load(buf)

    @classmethod
    def load(cls, path: str | Path) -> "ModelBundle":
        import torch
        payload = torch.load(path, map_location="cpu", weights_only=False)
        return cls(payload)

    def predict(self, text: str) -> tuple[str, float]:
        """
        Returns (predicted_label, confidence_probability).
        confidence is in [0, 1] — from CalibratedClassifierCV.predict_proba().
        """
        import numpy as np

        clean = _basic_clean(text)
        
        # If encoder exists, use it. Otherwise, raise a clear error that it's out.
        if self.encoder:
            embedding = self.encoder.encode(
                [clean],
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        else:
            raise RuntimeError("SentenceTransformer is not available, cannot encode text.")
            
        proba = self.svc.predict_proba(embedding)[0]
        idx = int(np.argmax(proba))
        return self.label_classes[idx], float(proba[idx])

    def predict_batch(self, texts: list[str]) -> list[tuple[str, float]]:
        """Efficient batch prediction."""
        import numpy as np
        
        clean = [_basic_clean(t) for t in texts]
        
        if self.encoder:
            embeddings = self.encoder.encode(
                clean,
                batch_size=64,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        else:
            raise RuntimeError("SentenceTransformer is not available.")
            
        probas = self.svc.predict_proba(embeddings)
        results = []
        for proba in probas:
            idx = int(np.argmax(proba))
            results.append((self.label_classes[idx], float(proba[idx])))
        return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train question + answer classifiers")
    p.add_argument(
        "--question-csv",
        required=True,
        help="Path to prodvi-random-questionset.csv (columns: Question, Label)",
    )
    p.add_argument(
        "--answer-csv",
        required=True,
        help="Path to prodvi-dataset-new4.csv (one column per category, text(Label) format)",
    )
    p.add_argument(
        "--output-dir",
        default="models",
        help="Directory to save .pt files (created if missing)",
    )
    p.add_argument(
        "--encoder",
        default=ENCODER_NAME,
        help=f"SentenceTransformer model name (default: {ENCODER_NAME})",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    question_csv = Path(args.question_csv)
    answer_csv   = Path(args.answer_csv)
    output_dir   = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load encoder once — shared by both trainers
    print(f"\nLoading encoder: {args.encoder}")
    encoder = SentenceTransformer(args.encoder)

    train_question_classifier(question_csv, encoder, output_dir)
    train_answer_classifier(answer_csv, encoder, output_dir)

    print("\n✓ Training complete.")
    print(f"  models/question_classifier.pt")
    print(f"  models/answer_classifier.pt")
    print("\nTo use at inference:")
    print("  from train import ModelBundle")
    print("  q_model = ModelBundle.load('models/question_classifier.pt')")
    print("  label, conf = q_model.predict('Does this person work well with others?')")


if __name__ == "__main__":
    main()