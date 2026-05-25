import json

nb_path = r"c:\Users\Joel\Desktop\Beihang University\Team-Pilot-Project\colab_train.ipynb"
with open(nb_path, encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    src = ''.join(cell.get('source', []))
    if ('src.models.train' in src and 'window_dir' in src
            and '--resume' not in src and cell['cell_type'] == 'code'):
        cell['source'] = [
            "import shutil, os, glob\n",
            "\n",
            "# Wipe ALL checkpoints from Drive so previous runs do not interfere\n",
            "drive_ckpt = '/content/drive/MyDrive/sentinel-gnss/checkpoints'\n",
            "local_ckpt = '/content/sentinel-gnss/results/models/checkpoints'\n",
            "\n",
            "for ckpt_path in [drive_ckpt, local_ckpt]:\n",
            "    if os.path.exists(ckpt_path):\n",
            "        for f in glob.glob(ckpt_path + '/*'):  # noqa: S605\n",
            "            os.remove(f)\n",
            "        print(f'Cleared: {ckpt_path}')\n",
            "\n",
            "%cd /content/sentinel-gnss\n",
            "# Trained WITHOUT SMOTE (SMOTE creates temporally incoherent synthetic windows).\n",
            "# Run 5 key fix: SPLIT_REASSIGN moves 7 test-only WARNING/DEGRADED sources to train.\n",
            "#   Root cause of runs 2-4: 84% of test WARNING came from sources NEVER in training.\n",
            "#   +1,971 train WARNING rows (+19%), +461 train DEGRADED rows (+11%).\n",
            "#   supervisor_vehicle_exp1_3_b intentionally left in test for held-out evaluation.\n",
            "# class_weights=[1.0, 2.0, 1.5], focal_gamma=1.0, label_smoothing=0.1, dropout=0.2.\n",
            "# Actual config printed at training start -- verify before reading results.\n",
            "#\n",
            "# EARLY STOPPING: balanced val subset (up to 500 per class). Patience=30.\n",
            "# stop_F1 = balanced-val metric; val_F1 = full-val (93% CLEAN, skewed) metric.\n",
            "!python -m src.models.train --batch_size 256 --window_dir data/processed/windows_no_smote",
        ]
        print("Step 5 updated.")
        break

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print("Saved.")
