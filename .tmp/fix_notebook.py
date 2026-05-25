import json
import os

nb_path = r"c:\Users\Joel\Desktop\Beihang University\Team-Pilot-Project\colab_train.ipynb"

with open(nb_path, encoding='utf-8') as f:
    nb = json.load(f)

# ── Fix Step 2: GPU check — raise RuntimeError instead of print warning ──────
for cell in nb['cells']:
    src = cell.get('source', [])
    joined = ''.join(src)
    if 'pip install -q imbalanced-learn' in joined and cell['cell_type'] == 'code':
        # Check if it still has the old print-warning pattern
        if "print('WARNING: No GPU" in joined:
            new_source = [
                "!pip install -q imbalanced-learn\n",
                "\n",
                "import torch\n",
                "print(f'PyTorch  : {torch.__version__}')\n",
                "print(f'CUDA     : {torch.cuda.is_available()}')\n",
                "if torch.cuda.is_available():\n",
                "    props = torch.cuda.get_device_properties(0)\n",
                "    print(f'GPU      : {torch.cuda.get_device_name(0)}')\n",
                "    print(f'VRAM     : {props.total_memory / 1e9:.1f} GB')\n",
                "else:\n",
                "    raise RuntimeError(\n",
                "        'NO GPU DETECTED.  Go to Runtime > Change runtime type > T4 GPU '\n",
                "        'and re-run from Step 1.  Training on CPU takes ~2 h and produces '\n",
                "        'significantly worse results (no AMP, different gradient dynamics).')",
            ]
            cell['source'] = new_source
            print("Step 2 GPU guard updated (print -> raise RuntimeError)")
        else:
            print("Step 2 GPU guard already has raise RuntimeError — no change needed")
        break

# ── Fix Step 5: update comments + fix garbled !python command ─────────────────
for cell in nb['cells']:
    src = cell.get('source', [])
    joined = ''.join(src)
    if ('src.models.train' in joined and 'window_dir' in joined
            and '--resume' not in joined and cell['cell_type'] == 'code'):
        new_source = [
            "import shutil, os, glob\n",
            "\n",
            "# Wipe ALL checkpoints from Drive so previous runs don't interfere\n",
            "drive_ckpt = '/content/drive/MyDrive/sentinel-gnss/checkpoints'\n",
            "local_ckpt = '/content/sentinel-gnss/results/models/checkpoints'\n",
            "\n",
            "for ckpt_path in [drive_ckpt, local_ckpt]:\n",
            "    if os.path.exists(ckpt_path):\n",
            "        for f in glob.glob(ckpt_path + '/*'):\n",
            "            os.remove(f)\n",
            "        print(f'Cleared: {ckpt_path}')\n",
            "\n",
            "%cd /content/sentinel-gnss\n",
            "# Trained WITHOUT SMOTE (SMOTE creates temporally incoherent synthetic windows).\n",
            "# Class weights [1.0, 2.0, 1.5] — DEGRADED reduced 2.0→1.5 (run 3: DEGRADED\n",
            "# precision 9.7%; model predicted DEGRADED for 46% of test set). Focal gamma\n",
            "# reduced 2.0→1.0: gamma=2 + class weights double-penalised minorities, causing\n",
            "# P(DEGRADED)>0.86 for 46% of test samples (severe miscalibration).\n",
            "# Label smoothing ε=0.1. Actual weights/gamma logged at training start — verify.\n",
            "#\n",
            "# EARLY STOPPING: uses a class-balanced val subset (up to 500 per class) rather\n",
            "# than the full val set which is 93% CLEAN after drone split reassignment.\n",
            "# Patience=30: gives the model more epochs to refine discrimination.\n",
            "# stop_F1 = balanced-val signal; val_F1 = full-val (skewed) signal.\n",
            "!python -m src.models.train --batch_size 256 --window_dir data/processed/windows_no_smote",
        ]
        cell['source'] = new_source
        print("Step 5 source updated (comments + !python command fixed)")
        break

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print("Notebook saved.")
