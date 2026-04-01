"""
test_models.py
--------------
Interactive tester for question_classifier.pt and answer_classifier.pt.

Usage:
    python test_models.py --model-dir models/

Controls:
    q  → test question classifier
    a  → test answer classifier
    b  → test both on the same input
    r  → run a random batch of built-in sample inputs
    x  → exit
"""

import argparse
import random
from pathlib import Path

# ── sample inputs for random-batch mode ────────────────────────────────────

SAMPLE_QUESTIONS = [
    "Does this person communicate clearly with the team?",
    "How well does this employee handle deadlines?",
    "Is this person open to new ideas and change?",
    "Does this individual take initiative without being asked?",
    "How does this person handle conflict with colleagues?",
    "Does this employee show up on time consistently?",
    "How well does this person solve difficult problems?",
    "Does this person mentor or help junior team members?",
    "How effectively does this employee manage their workload?",
    "Does this person stay calm under pressure?",
    "How creative is this person in their approach to work?",
    "Does this employee take ownership of their mistakes?",
    "How well does this person work in a team setting?",
    "Does this person actively listen during meetings?",
    "How motivated is this employee to improve their skills?",
    # deliberately off-topic to test Out of Scope
    "What is the capital of France?",
    "Can you recommend a good restaurant nearby?",
    "What is 2 + 2?",
]

SAMPLE_ANSWERS = [
    "She always delivers her work on time and never misses a deadline.",
    "He struggles to communicate his ideas clearly to the rest of the team.",
    "This person is extremely creative and brings fresh perspectives to every project.",
    "They often arrive late and it disrupts the morning standup.",
    "She is a natural leader who motivates everyone around her.",
    "He tends to avoid conflict rather than addressing issues directly.",
    "This employee is very adaptable and thrives in changing environments.",
    "She rarely takes initiative and waits to be told what to do.",
    "He is highly efficient and consistently produces high-quality work.",
    "This person struggles with problem solving when things get complex.",
    "She is emotionally intelligent and handles feedback very well.",
    "He is cooperative and always willing to help teammates.",
    "This employee shows strong self-motivation and continuously upskills.",
    "She has great innovative ideas but sometimes fails to execute them.",
    "He needs improvement in punctuality and time management.",
]


# ── helpers ────────────────────────────────────────────────────────────────

def _bar(confidence: float, width: int = 30) -> str:
    filled = int(confidence * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {confidence:.1%}"


def _print_result(label: str, confidence: float, model_type: str) -> None:
    color = "\033[92m" if confidence >= 0.6 else "\033[93m" if confidence >= 0.4 else "\033[91m"
    reset = "\033[0m"
    print(f"\n  ┌─ {model_type}")
    print(f"  │  Label      : {color}{label}{reset}")
    print(f"  │  Confidence : {_bar(confidence)}")
    print(f"  └{'─' * 40}")


def _test_question(bundle, text: str) -> None:
    label, conf = bundle.predict(text)
    _print_result(label, conf, "Question Classifier")


def _test_answer(bundle, text: str) -> None:
    label, conf = bundle.predict(text)
    _print_result(label, conf, "Answer Classifier")


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Test question + answer classifier models")
    parser.add_argument("--model-dir", default="models/", help="Directory containing .pt files")
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    q_path = model_dir / "question_classifier.pt"
    a_path = model_dir / "answer_classifier.pt"

    # Lazy imports so the script fails clearly if train.py isn't on the path
    try:
        from train import ModelBundle
    except ImportError:
        print("ERROR: Could not import ModelBundle from train.py.")
        print("Make sure train.py is in the same directory as this script.")
        return

    print("\nLoading models …")
    q_bundle = ModelBundle.load(q_path) if q_path.exists() else None
    a_bundle = ModelBundle.load(a_path) if a_path.exists() else None

    if not q_bundle:
        print(f"  [WARN] question_classifier.pt not found at {q_path}")
    else:
        print(f"  ✓ Question classifier loaded  ({len(q_bundle.label_classes)} classes)")
        print(f"    CV F1: {q_bundle.metrics.get('weighted_f1', 'n/a'):.4f}")

    if not a_bundle:
        print(f"  [WARN] answer_classifier.pt not found at {a_path}")
    else:
        print(f"  ✓ Answer classifier loaded    ({len(a_bundle.label_classes)} classes)")
        print(f"    CV F1: {a_bundle.metrics.get('weighted_f1', 'n/a'):.4f}")

    print("\n" + "─" * 50)
    print("  q  → test question classifier")
    print("  a  → test answer classifier")
    print("  b  → test both on same input")
    print("  r  → random batch (5 questions + 5 answers)")
    print("  x  → exit")
    print("─" * 50)

    while True:
        try:
            cmd = input("\nCommand (q/a/b/r/x): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if cmd == "x":
            print("Bye.")
            break

        elif cmd == "q":
            if not q_bundle:
                print("  Question classifier not loaded.")
                continue
            text = input("  Enter question: ").strip()
            if text:
                _test_question(q_bundle, text)

        elif cmd == "a":
            if not a_bundle:
                print("  Answer classifier not loaded.")
                continue
            text = input("  Enter answer/comment: ").strip()
            if text:
                _test_answer(a_bundle, text)

        elif cmd == "b":
            text = input("  Enter text: ").strip()
            if not text:
                continue
            if q_bundle:
                _test_question(q_bundle, text)
            if a_bundle:
                _test_answer(a_bundle, text)

        elif cmd == "r":
            questions = random.sample(SAMPLE_QUESTIONS, min(5, len(SAMPLE_QUESTIONS)))
            answers   = random.sample(SAMPLE_ANSWERS,   min(5, len(SAMPLE_ANSWERS)))

            if q_bundle:
                print("\n  ── Random questions ──")
                for q in questions:
                    print(f'\n  "{q}"')
                    _test_question(q_bundle, q)

            if a_bundle:
                print("\n  ── Random answers ──")
                for a in answers:
                    print(f'\n  "{a}"')
                    _test_answer(a_bundle, a)

        else:
            print("  Unknown command. Use q / a / b / r / x.")


if __name__ == "__main__":
    main()
