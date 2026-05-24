import json

nb_path = r"c:\Users\Joel\Desktop\Beihang University\Team-Pilot-Project\colab_train.ipynb"

with open(nb_path, encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    src = ''.join(cell.get('source', []))
    if 'feature_prep' in src and 'no_smote' in src and cell['cell_type'] == 'code':
        cell['source'] = [
            "%cd /content/sentinel-gnss\n",
            "# Drone sessions (supervisor_drone_1, _2, _12) are EXCLUDED by default:\n",
            "#   UAV open-sky data is not vehicular -- different GNSS dynamics, 100% CLEAN.\n",
            "#   Use --include_drones to override.  Extra exclusions: --exclude_sources nclt\n",
            "# --force ensures y_0s label is rebuilt even if .npz cache already exists.\n",
            "!python -m src.models.feature_prep --force\n",
            "\n",
            "# Build no-SMOTE windows (used by deep model)\n",
            "!python -m src.models.feature_prep --no_smote --force\n",
            "\n",
            "# Sanity check\n",
            "import numpy as np\n",
            "\n",
            "for tag, wdir in [('SMOTE -- baselines', 'windows'), ('no-SMOTE -- deep model', 'windows_no_smote')]:\n",
            "    print(f'\\nWindow shapes ({tag}):')\n",
            "    for split in ('train', 'val', 'test'):\n",
            "        d = np.load(f'data/processed/{wdir}/{split}.npz')\n",
            "        y0 = 'y_0s present' if 'y_0s' in d else 'y_0s MISSING'\n",
            "        c = np.sum(d['y_5s'] == 0); w = np.sum(d['y_5s'] == 1); g = np.sum(d['y_5s'] == 2)\n",
            "        print(f'  {split:5s}  X={d[\"X\"].shape}  CLEAN={c:,}  WARNING={w:,}  DEGRADED={g:,}  [{y0}]')\n",
        ]
        print("Step 4 cell updated")
        break

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print("Saved.")
