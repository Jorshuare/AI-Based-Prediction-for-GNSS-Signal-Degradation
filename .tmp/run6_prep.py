"""Update colab_train.ipynb Step 5 cell for Run 6 and syntax-check modified files."""
import ast
import json
import sys

# ── 1. Syntax-check modified Python files ─────────────────────────────────
for fname in [
    "src/models/evaluate.py",
    "src/models/feature_prep.py",
    "src/models/train.py",
]:
    try:
        ast.parse(open(fname, encoding="utf-8").read())
        print(f"  OK  {fname}")
    except SyntaxError as e:
        print(f"  FAIL  {fname}: {e}")
        sys.exit(1)

# ── 2. Update notebook Step 5 cell ────────────────────────────────────────
with open("colab_train.ipynb", encoding="utf-8") as f:
    nb = json.load(f)

# Find cell 11 (Step 5 — training) by looking for the training command
target_idx = None
for i, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    if "src.models.train --batch_size 256 --window_dir" in src and "shutil" in src:
        target_idx = i
        break

if target_idx is None:
    print("ERROR: could not find Step 5 cell in notebook")
    sys.exit(1)

old_src = nb["cells"][target_idx]["source"]
# Keep boilerplate lines before the first comment about SMOTE
cut = next(
    i for i, line in enumerate(old_src)
    if line.startswith("# Trained WITHOUT SMOTE")
)

new_comment = [
    "# Trained WITHOUT SMOTE (SMOTE creates temporally incoherent synthetic windows).\n",
    "# -- Run 6 changes (vs Run 5 baseline +5s MacroF1=0.467) --\n",
    "# 1. Constrained threshold tuning: precision floor P >= 0.30 for every class.\n",
    "#    Run 5: WARNING P=0.163 R=1.000 -- tuner set t_warn so low that 53% of\n",
    "#    test was predicted WARNING. The floor prevents this whack-a-mole collapse.\n",
    "# 2. Larger model: d_model=128, n_heads=8, d_ff=512, lstm_hidden=256 (~1.5M params)\n",
    "#    with dropout=0.3 to compensate for increased capacity.\n",
    "# 3. Delta features: pdop_delta + hdop_delta added (34 -> 36 features).\n",
    "#    Run 5 saliency: pdop/hdop were top-2 features; rate-of-change is a\n",
    "#    leading degradation indicator (DOP spike = geometry worsening).\n",
    "# 4. Patience=50: give the larger model more room to find its best epoch.\n",
    "#    Run 5 best epoch was epoch 5 -- consistently stopping too early.\n",
    "# class_weights=[1.0, 2.0, 1.5], focal_gamma=1.0, label_smoothing=0.1 unchanged.\n",
    "# n_features auto-inferred at runtime (no config/data mismatch risk).\n",
    "#\n",
    "# EARLY STOPPING: balanced val subset (up to 500 per class). Patience=50.\n",
    "# stop_F1 = balanced-val metric; val_F1 = full-val (93% CLEAN, skewed) metric.\n",
    "!python -m src.models.train --batch_size 256 --window_dir data/processed/windows_no_smote",
]

nb["cells"][target_idx]["source"] = old_src[:cut] + new_comment

with open("colab_train.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"  OK  colab_train.ipynb (cell {target_idx}) updated")
print("\nAll checks passed. Ready to commit.")
