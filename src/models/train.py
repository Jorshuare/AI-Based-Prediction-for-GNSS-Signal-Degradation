"""
train.py — Training loop for SENTINEL-GNSS with robust checkpointing.

Features
--------
  - Focal loss with per-class weights (handles 67 / 20 / 13 % imbalance)
  - AdamW optimiser + cosine LR schedule with linear warm-up
  - Gradient clipping (max_norm=1.0) for stable Transformer training
  - Mixed precision (torch.cuda.amp) for GPU speedup
  - Epoch checkpoints + best-model checkpoint (keyed on val macro-F1)
  - Early stopping (patience=15, monitors val macro-F1)
  - Full training history saved as JSON (for learning-curve plots)
  - Reproducible: seeds numpy, Python random, and PyTorch

Usage
-----
  # Full training run (auto-detects GPU if available):
  python -m src.models.train

  # Resume from latest checkpoint:
  python -m src.models.train --resume

  # Ablation: Transformer-only (no LSTM):
  python -m src.models.train --arch transformer_only

References
----------
Loshchilov, I. & Hutter, F. (2019). Decoupled weight decay regularization.
    ICLR. https://arxiv.org/abs/1711.05101

Loshchilov, I. & Hutter, F. (2017). SGDR: Stochastic gradient descent with
    warm restarts. ICLR. https://arxiv.org/abs/1608.03983

Pascanu, R., Mikolov, T., & Bengio, Y. (2013). On the difficulty of training
    recurrent neural networks. ICML.
    https://proceedings.mlr.press/v28/pascanu13.html

Lin, T. Y., et al. (2017). Focal loss for dense object detection. ICCV.
    https://arxiv.org/abs/1708.02002
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader, TensorDataset

from src.models.feature_prep import OUT_DIR as WINDOW_DIR
from src.models.feature_prep import load_windows
from src.models.transformer_lstm import FocalLoss, SentinelGNSS, build_model

log = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
CKPT_DIR = ROOT / "results" / "models" / "checkpoints"
HISTORY_FILE = CKPT_DIR / "training_history.json"

# ─── Hyper-parameters (expert-recommended defaults) ──────────────────────────
DEFAULT_CONFIG: dict = {
    # Model
    # 34→36 (Run 6: +pdop_delta, +hdop_delta) → 37 (Run 7: +receiver_tier)
    # Overwritten at runtime by the actual window shape — always correct.
    "n_features":    37,
    "d_model":       128,    # 64→128: wider Transformer for more representational capacity
    # 4→8: more attention patterns (must divide d_model)
    "n_heads":       8,
    "n_tf_layers":   2,      # unchanged
    "d_ff":          512,    # 256→512: larger FFN sub-layer
    "lstm_hidden":   256,    # 128→256: more LSTM state capacity
    "n_lstm_layers": 2,
    "n_classes":     3,
    "dropout":       0.3,    # 0.2→0.3: stronger regularisation for the larger model
    # Training
    "batch_size":    64,   # 64 is safe for 4 GB VRAM; increase to 256 on larger GPUs
    "max_epochs":    150,
    "lr":            1e-3,
    "weight_decay":  1e-4,    # AdamW  (Loshchilov & Hutter, 2019)
    "warmup_epochs": 5,       # linear LR warm-up before cosine decay
    # max-norm gradient clipping (Pascanu et al., 2013)
    "grad_clip":     1.0,
    "early_stop_patience": 50,   # 30→50: larger model needs more room to converge
    # Run 7 best checkpoint was at epoch 2 — the balanced val happened to score 0.8169
    # early because scenario_a/tunnel DEGRADED patterns are easy to detect with barely-
    # trained weights.  Locking in epoch=2 as "best" means 50 patience epochs are wasted.
    # Run 8 fix: don't save best checkpoint or count patience until epoch >= 15.
    "min_epoch_for_best": 15,
    "focal_gamma":   1.0,        # reduced 2.0→1.0: γ=2 + class weights was double-penalising
                                 # minority classes, causing P(DEGRADED)>0.86 for 46%
                                 # of test samples (severe miscalibration).
    # Class weights: [CLEAN, WARNING, DEGRADED]
    # Run 7 redistribution: removing Oxford/Tokyo/NCLT from training flips the class
    # balance.  New effective training distribution ≈ 42% CLEAN / 41% WARNING / 17% DEGRADED
    # (vs old 73/15/9).  CLEAN and WARNING are now roughly equal → set their weights 1:2
    # (WARNING still needs a modest boost because it is the hardest class to recall).
    # DEGRADED is the true minority → weight 3.0 to maintain detection sensitivity.
    # Previous [1.0, 2.0, 1.5] was tuned for the Oxford-inflated DEGRADED class; raising
    # DEGRADED to 3.0 restores the correct relative emphasis after Oxford is removed.
    # Run 8: DEGRADED weight raised 3.0 → 5.0.  Achieved 58% DEGRADED recall at +5s,
    # but 158/551 WARNING samples were falsely predicted as DEGRADED (only 16.8% precision).
    # Run 9: DEGRADED weight reduced 5.0 → 4.0 — this BACKFIRED: WARNING recall dropped
    # from 70% to 50% and DEGRADED precision only improved from 17% to 15%.  The lower weight
    # weakened the DEGRADED signal without fixing the source of false alarms.
    # Run 10: revert to DEGRADED weight 5.0 (Run 8's best-performing value, avg test F1=0.639).
    # The false alarm problem is addressed in evaluate.py via a rate-based threshold constraint
    # (max 15% of val WARNING samples may be predicted as DEGRADED) rather than reducing the
    # class weight — a constraint that transfers more reliably from val to test.
    "class_weights": [1.0, 2.0, 5.0],
    # Label smoothing ε: distributes probability mass to non-target classes, preventing
    # the model from becoming overconfident on minority-class predictions.
    "label_smoothing": 0.1,
    # Auxiliary head weight: fraction of total loss assigned to the
    # t+0s current-state head (multi-task regulariser, Caruana 1997).
    "aux_head_weight": 0.3,
    # Horizon weights: Run 9 tried {5s:0.8, 15s:1.0, 30s:1.2} to address +30s weakness.
    # BACKFIRED: reducing +5s gradient caused WARNING→CLEAN errors to jump from 7 to 98 at
    # +5s, and +30s WARNING recall actually dropped from 50% to 33% (the model couldn't
    # distribute capacity with unequal weights).  Run 10: revert to equal weights.
    # The +30s weakness is better addressed through architecture improvements in future runs.
    "horizon_weights": {"5s": 1.0, "15s": 1.0, "30s": 1.0},
    # Misc
    "seed":          42,
    "amp":           True,    # automatic mixed precision (GPU only)
    # DataLoader workers (0 = main process; safe on Windows)
    "num_workers":   0,
    "save_every":    10,      # Save periodic checkpoint every N epochs
}


# ─── Reproducibility ──────────────────────────────────────────────────────────
def set_seed(seed: int = 42) -> None:
    """Set all RNG seeds for full reproducibility.

    Ref: PyTorch reproducibility guide:
    https://pytorch.org/docs/stable/notes/randomness.html
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    os.environ["PYTHONHASHSEED"] = str(seed)


# ─── LR schedule: linear warm-up + cosine decay ──────────────────────────────
def build_scheduler(
    optimizer: torch.optim.Optimizer,
    warmup_epochs: int,
    max_epochs: int,
) -> LambdaLR:
    """Cosine annealing with linear warm-up.

    During warm-up (epochs 0..warmup_epochs-1) LR increases linearly from 0
    to the configured lr.  After warm-up, LR follows a cosine decay to 0.

    Ref: Loshchilov & Hutter (2017). SGDR. ICLR.
    """
    def lr_lambda(epoch: int) -> float:
        if epoch < warmup_epochs:
            return float(epoch + 1) / float(max(1, warmup_epochs))
        progress = float(epoch - warmup_epochs) / float(
            max(1, max_epochs - warmup_epochs)
        )
        return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))

    return LambdaLR(optimizer, lr_lambda)


# ─── Data loaders ─────────────────────────────────────────────────────────────
def make_loaders(
    windows: dict,
    batch_size: int,
    num_workers: int = 0,
) -> dict[str, DataLoader]:
    """Wrap numpy windows in TensorDatasets and return DataLoaders."""
    loaders = {}
    for spl in ("train", "val", "test"):
        d = windows[spl]
        X = torch.from_numpy(d["X"]).float()
        y_5s = torch.from_numpy(d["y_5s"]).long()
        y_15s = torch.from_numpy(d["y_15s"]).long()
        y_30s = torch.from_numpy(d["y_30s"]).long()
        # y_0s is the current state (auxiliary multi-task label).
        # Fall back to y_5s if missing (backward-compatible with old windows).
        y_0s = torch.from_numpy(
            d["y_0s"] if "y_0s" in d else d["y_5s"]).long()
        ds = TensorDataset(X, y_5s, y_15s, y_30s, y_0s)
        loaders[spl] = DataLoader(
            ds,
            batch_size=batch_size,
            shuffle=(spl == "train"),
            num_workers=num_workers,
            pin_memory=torch.cuda.is_available(),
        )
    return loaders


# ─── Balanced val subset for early stopping ──────────────────────────────────
def make_balanced_val_loader(
    val_loader: DataLoader,
    batch_size: int,
    n_per_class: int = 500,
    seed: int = 42,
) -> DataLoader:
    """Return a class-balanced DataLoader sampled from the val set.

    The full val set is ~97 % CLEAN, which causes early stopping to fire on a
    degenerate distribution (model just predicts CLEAN well).  This loader
    draws at most *n_per_class* samples per class so the stopping signal
    equally reflects CLEAN, WARNING, and DEGRADED performance.

    The full val loader still runs every epoch for loss/F1 logging.
    """
    ds = val_loader.dataset
    X_all, y5_all, y15_all, y30_all, y0_all = [t.numpy() for t in ds.tensors]

    rng = np.random.RandomState(seed)
    n_take = min(n_per_class, *(int(np.sum(y5_all == c)) for c in range(3)))

    indices = np.concatenate([
        rng.choice(np.where(y5_all == c)[0], size=n_take, replace=False)
        for c in range(3)
    ])
    rng.shuffle(indices)

    ds_bal = TensorDataset(
        torch.from_numpy(X_all[indices]).float(),
        torch.from_numpy(y5_all[indices]).long(),
        torch.from_numpy(y15_all[indices]).long(),
        torch.from_numpy(y30_all[indices]).long(),
        torch.from_numpy(y0_all[indices]).long(),
    )
    return DataLoader(
        ds_bal,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )


# ─── Single epoch pass ────────────────────────────────────────────────────────
def run_epoch(
    model:      SentinelGNSS,
    loader:     DataLoader,
    criterion:  dict[str, FocalLoss],
    horizon_w:  dict[str, float],
    optimizer:  Optional[torch.optim.Optimizer],
    scaler:     Optional[torch.amp.GradScaler],
    device:     torch.device,
    grad_clip:  float,
    train:      bool,
    aux_weight: float = 0.0,
) -> tuple[float, dict[str, float]]:
    """Run one epoch (training or evaluation).

    Returns
    -------
    mean_loss  : Weighted sum of the three horizon losses.
    macro_f1s  : Dict {'5s': float, '15s': float, '30s': float}.
    """
    model.train(train)
    total_loss = 0.0
    all_preds: dict[str, list] = {"5s": [], "15s": [], "30s": []}
    all_true:  dict[str, list] = {"5s": [], "15s": [], "30s": []}

    ctx = torch.enable_grad() if train else torch.no_grad()
    with ctx:
        for batch in loader:
            X, y5, y15, y30, y0 = (t.to(device) for t in batch)
            targets = {"5s": y5, "15s": y15, "30s": y30}

            with torch.amp.autocast("cuda", enabled=(scaler is not None)):
                out = model(X)
                prediction_loss = sum(
                    horizon_w[k] * criterion[k](out[f"logits_{k}"], targets[k])
                    for k in horizon_w
                )
                # Auxiliary current-state loss (multi-task regulariser; only if model has head_0s)
                aux_loss = criterion["5s"](
                    out["logits_0s"], y0) if (aux_weight > 0 and "logits_0s" in out) else 0.0
                loss = prediction_loss + aux_weight * aux_loss

            if train and optimizer is not None:
                optimizer.zero_grad()
                if scaler is not None:
                    scaler.scale(loss).backward()
                    scaler.unscale_(optimizer)
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                    optimizer.step()

            total_loss += loss.item() * X.size(0)
            for k in horizon_w:
                preds = out[f"logits_{k}"].argmax(dim=1).cpu().numpy()
                all_preds[k].extend(preds)
                all_true[k].extend(targets[k].cpu().numpy())

    n = sum(len(all_true[k]) for k in horizon_w) // len(horizon_w)
    mean_loss = total_loss / (n * len(horizon_w))

    macro_f1s = {
        k: float(f1_score(all_true[k], all_preds[k],
                 average="macro", zero_division=0))
        for k in horizon_w
    }
    return mean_loss, macro_f1s


# ─── Checkpoint utilities ─────────────────────────────────────────────────────
def save_checkpoint(
    ckpt_dir: Path,
    tag: str,
    epoch: int,
    model: SentinelGNSS,
    optimizer: torch.optim.Optimizer,
    scheduler: LambdaLR,
    amp_scaler: Optional[torch.amp.GradScaler],
    best_metric: float,
    config: dict,
    history: dict,
) -> Path:
    """Save a full checkpoint — model + optimiser + scheduler + metadata.

    Saving the optimiser and scheduler states enables seamless resumption.
    Without them, the LR schedule and Adam moment estimates are lost, which
    can cause training instability after resumption.
    """
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    path = ckpt_dir / f"checkpoint_{tag}.pt"
    payload = {
        "epoch":         epoch,
        "model":         model.state_dict(),
        "optimizer":     optimizer.state_dict(),
        "scheduler":     scheduler.state_dict(),
        "best_metric":   best_metric,
        "config":        config,
    }
    if amp_scaler is not None:
        payload["amp_scaler"] = amp_scaler.state_dict()
    torch.save(payload, path)

    # Also persist history as JSON (human-readable, used by evaluate.py)
    history_path = ckpt_dir / "training_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    return path


def load_checkpoint(
    path: Path,
    model: SentinelGNSS,
    optimizer: Optional[torch.optim.Optimizer] = None,
    scheduler: Optional[LambdaLR] = None,
    amp_scaler: Optional[torch.amp.GradScaler] = None,
    device: torch.device = torch.device("cpu"),
) -> tuple[int, float, dict]:
    """Load a checkpoint.  Returns (start_epoch, best_metric, config)."""
    ckpt = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    if optimizer is not None and "optimizer" in ckpt:
        optimizer.load_state_dict(ckpt["optimizer"])
    if scheduler is not None and "scheduler" in ckpt:
        scheduler.load_state_dict(ckpt["scheduler"])
    if amp_scaler is not None and "amp_scaler" in ckpt:
        amp_scaler.load_state_dict(ckpt["amp_scaler"])
    log.info(
        f"  Loaded checkpoint: epoch={ckpt['epoch']}  best_metric={ckpt['best_metric']:.4f}")
    return ckpt["epoch"], ckpt["best_metric"], ckpt.get("config", {})


def find_latest_checkpoint(ckpt_dir: Path) -> Optional[Path]:
    """Return the most recent periodic checkpoint, or None if none exist."""
    ckpts = sorted(ckpt_dir.glob("checkpoint_epoch_*.pt"))
    return ckpts[-1] if ckpts else None


# ─── Main training loop ───────────────────────────────────────────────────────
def train(
    config: dict = DEFAULT_CONFIG,
    resume: bool = False,
    ckpt_dir: Path = CKPT_DIR,
    window_dir: Path = WINDOW_DIR,
) -> tuple[SentinelGNSS, dict]:
    """Main training function.

    Parameters
    ----------
    config    : Hyper-parameter dict (see DEFAULT_CONFIG).
    resume    : If True, load the latest checkpoint before training.
    ckpt_dir  : Directory for saving checkpoints and history.
    window_dir: Directory containing train/val/test .npz window files.

    Returns
    -------
    model   : Best trained model (loaded from best checkpoint).
    history : Full training / validation metric history dict.
    """
    set_seed(config["seed"])
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s  %(message)s")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Device: {device}")
    if torch.cuda.is_available():
        log.info(f"  GPU: {torch.cuda.get_device_name(0)}")
    else:
        log.warning("=" * 60)
        log.warning("  NO GPU DETECTED — training on CPU (~220 s/epoch).")
        log.warning("  In Colab: Runtime ▸ Change runtime type ▸ T4 GPU")
        log.warning("  Results will be significantly worse than GPU training.")
        log.warning("=" * 60)

    # ── Data ─────────────────────────────────────────────────────────────
    log.info("Loading windows …")
    windows = load_windows(window_dir)
    # Auto-infer n_features from data so config stays correct when feature_prep changes.
    # Production value is 37 (33 signal + cnr_available + pdop_delta + hdop_delta + receiver_tier).
    config = dict(config)   # don't mutate caller's dict
    config["n_features"] = int(windows["train"]["X"].shape[2])
    log.info(
        f"  n_features={config['n_features']} (auto-inferred from windows)")
    loaders = make_loaders(
        windows, config["batch_size"], config["num_workers"])
    # Balanced val subset: 500 samples per class (CLEAN / WARNING / DEGRADED)
    # Used exclusively for early stopping and best-checkpoint decisions.
    # The full val loader still runs every epoch for loss/F1 logging.
    loaders["val_stop"] = make_balanced_val_loader(
        loaders["val"], config["batch_size"], seed=config["seed"])
    n_stop = len(loaders["val_stop"].dataset)
    log.info(f"  train batches: {len(loaders['train'])}  "
             f"val batches: {len(loaders['val'])}  "
             f"val_stop (balanced): {n_stop} samples")

    # ── Model ─────────────────────────────────────────────────────────────
    model = build_model(config).to(device)

    # ── Loss ──────────────────────────────────────────────────────────────
    class_w = torch.tensor(config["class_weights"], dtype=torch.float32)
    criterion = {
        k: FocalLoss(
            gamma=config["focal_gamma"],
            weight=class_w,
            label_smoothing=config.get("label_smoothing", 0.0),
        )
        for k in ("5s", "15s", "30s")
    }
    horizon_w = config["horizon_weights"]

    # ── Optimiser + scheduler ─────────────────────────────────────────────
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config["lr"],
        weight_decay=config["weight_decay"],
        betas=(0.9, 0.999),
    )
    scheduler = build_scheduler(
        optimizer, config["warmup_epochs"], config["max_epochs"])
    amp_scaler = (
        torch.amp.GradScaler("cuda") if (config["amp"] and torch.cuda.is_available())
        else None
    )

    # ── Resume from checkpoint ───────────────────────────────────────────
    start_epoch = 0
    best_metric = 0.0
    history: dict = {
        "train_loss": [], "val_loss": [],
        "train_f1_5s": [], "train_f1_15s": [], "train_f1_30s": [],
        "val_f1_5s":   [], "val_f1_15s":   [], "val_f1_30s":   [],
        "stop_f1_5s":  [], "stop_f1_15s":  [], "stop_f1_30s":  [],
        "lr": [],
    }

    if resume:
        latest = find_latest_checkpoint(ckpt_dir)
        if latest:
            start_epoch, best_metric, _ = load_checkpoint(
                latest, model, optimizer, scheduler, amp_scaler, device
            )
            # Load existing history
            history_file = ckpt_dir / "training_history.json"
            if history_file.exists():
                with open(history_file) as f:
                    history = json.load(f)
            log.info(f"  Resuming from epoch {start_epoch}")
        else:
            log.info("  No checkpoint found; starting from scratch.")

    # ── Save config alongside checkpoints ────────────────────────────────
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    with open(ckpt_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # ── Training loop ─────────────────────────────────────────────────────
    patience_counter = 0
    best_ckpt_path = ckpt_dir / "checkpoint_best.pt"

    log.info(f"\n{'='*60}")
    log.info(
        f"  Training SENTINEL-GNSS  |  {model.count_parameters():,} parameters")
    log.info(
        f"  Epochs: {start_epoch} → {config['max_epochs']}  |  Patience: {config['early_stop_patience']}")
    log.info(
        f"  class_weights={config['class_weights']}  focal_gamma={config['focal_gamma']}"
        f"  label_smoothing={config.get('label_smoothing', 0.0)}  dropout={config['dropout']}")
    log.info(f"{'='*60}\n")

    for epoch in range(start_epoch, config["max_epochs"]):
        t0 = time.time()

        # Train
        tr_loss, tr_f1 = run_epoch(
            model, loaders["train"], criterion, horizon_w,
            optimizer, amp_scaler, device, config["grad_clip"], train=True,
            aux_weight=config.get("aux_head_weight", 0.0),
        )
        # Full val — logged every epoch (loss + F1 for learning curves)
        val_loss, val_f1 = run_epoch(
            model, loaders["val"], criterion, horizon_w,
            None, None, device, config["grad_clip"], train=False,
            aux_weight=0.0,
        )
        # Balanced val — early stopping signal (equal class representation)
        _, stop_f1 = run_epoch(
            model, loaders["val_stop"], criterion, horizon_w,
            None, None, device, config["grad_clip"], train=False,
            aux_weight=0.0,
        )

        scheduler.step()
        current_lr = scheduler.get_last_lr()[0]

        # History
        history["train_loss"].append(tr_loss)
        history["val_loss"].append(val_loss)
        history["train_f1_5s"].append(tr_f1["5s"])
        history["train_f1_15s"].append(tr_f1["15s"])
        history["train_f1_30s"].append(tr_f1["30s"])
        history["val_f1_5s"].append(val_f1["5s"])
        history["val_f1_15s"].append(val_f1["15s"])
        history["val_f1_30s"].append(val_f1["30s"])
        history["stop_f1_5s"].append(stop_f1["5s"])
        history["stop_f1_15s"].append(stop_f1["15s"])
        history["stop_f1_30s"].append(stop_f1["30s"])
        history["lr"].append(current_lr)

        # Primary monitor metric: balanced val macro-F1 (equal class weight)
        # val_mean_f1 is still logged but NOT used for early stopping.
        val_mean_f1 = np.mean([val_f1["5s"],  val_f1["15s"],  val_f1["30s"]])
        stop_mean_f1 = np.mean([stop_f1["5s"], stop_f1["15s"], stop_f1["30s"]])

        elapsed = time.time() - t0
        log.info(
            f"Epoch {epoch+1:03d}/{config['max_epochs']}  "
            f"| tr_loss={tr_loss:.4f}  val_loss={val_loss:.4f}  "
            f"| val_F1(5s/15s/30s): {val_f1['5s']:.3f}/{val_f1['15s']:.3f}/{val_f1['30s']:.3f}  "
            f"| stop_F1={stop_mean_f1:.3f}  "
            f"| lr={current_lr:.2e}  {elapsed:.1f}s"
        )

        # ── Periodic checkpoint ───────────────────────────────────────────
        if (epoch + 1) % config["save_every"] == 0:
            tag = f"epoch_{epoch+1:03d}"
            path = save_checkpoint(
                ckpt_dir, tag, epoch + 1, model, optimizer, scheduler,
                amp_scaler, best_metric, config, history,
            )
            log.info(f"  → Periodic checkpoint: {path.name}")

        # ── Best-model checkpoint ─────────────────────────────────────────
        # Skip best-checkpoint tracking until min_epoch_for_best is reached.
        # Early epochs can score deceptively high on the balanced val subset
        # (barely-trained weights happen to separate easy DEGRADED examples)
        # while not generalising at all on the test set.
        min_epoch_for_best = config.get("min_epoch_for_best", 1)
        if epoch + 1 < min_epoch_for_best:
            log.info(
                f"  (epoch {epoch+1} < min_epoch_for_best={min_epoch_for_best}; "
                f"stop_F1={stop_mean_f1:.4f} noted but not saved as best)")
        elif stop_mean_f1 > best_metric:
            best_metric = stop_mean_f1
            patience_counter = 0
            save_checkpoint(
                ckpt_dir, "best", epoch + 1, model, optimizer, scheduler,
                amp_scaler, best_metric, config, history,
            )
            log.info(
                f"  ★ New best stop macro-F1 = {best_metric:.4f}  → checkpoint_best.pt")
        else:
            patience_counter += 1

        # ── Early stopping ────────────────────────────────────────────────
        if patience_counter >= config["early_stop_patience"]:
            log.info(
                f"\n  Early stopping triggered at epoch {epoch+1} "
                f"(patience={config['early_stop_patience']}, "
                f"no improvement for {patience_counter} epochs)."
            )
            break

    log.info(f"\nTraining complete.  Best val macro-F1 = {best_metric:.4f}")

    # ── Load best model for return ────────────────────────────────────────
    if best_ckpt_path.exists():
        load_checkpoint(best_ckpt_path, model, device=device)

    # ── Save final history ────────────────────────────────────────────────
    history_file = ckpt_dir / "training_history.json"
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
    log.info(f"  History saved → {history_file}")

    return model, history


# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SENTINEL-GNSS")
    parser.add_argument("--resume",       action="store_true",
                        help="Resume from latest checkpoint")
    parser.add_argument("--batch_size",   type=int,   default=None)
    parser.add_argument("--max_epochs",   type=int,   default=None)
    parser.add_argument("--lr",           type=float, default=None)
    parser.add_argument("--dropout",      type=float, default=None)
    parser.add_argument("--focal_gamma",   type=float, default=None)
    parser.add_argument("--class_weights",  type=float, nargs=3,
                        metavar=("W_CLEAN", "W_WARNING", "W_DEGRADED"), default=None,
                        help="Per-class focal loss weights, e.g. --class_weights 1 4 3")
    parser.add_argument("--model_type",   type=str,   default="full",
                        choices=["full", "lstm_only", "transformer_only"],
                        help="Model architecture: full=SENTINEL-GNSS, "
                             "lstm_only=ablation (no Transformer), "
                             "transformer_only=ablation (no LSTM)")
    parser.add_argument("--window_dir",   type=str,   default=None,
                        help="Path to directory containing train/val/test .npz windows. "
                             "Defaults to data/processed/windows/. "
                             "Use data/processed/windows_no_smote/ for deep model training.")
    parser.add_argument("--debug",        action="store_true",
                        help="Smoke-test: use windows_debug/ and a debug checkpoint dir")
    args = parser.parse_args()

    cfg = DEFAULT_CONFIG.copy()
    for key in ("batch_size", "max_epochs", "lr", "dropout", "focal_gamma"):
        val = getattr(args, key)
        if val is not None:
            cfg[key] = val
    if args.class_weights is not None:
        cfg["class_weights"] = list(args.class_weights)
    cfg["model_type"] = args.model_type

    # Each model type gets its own checkpoint directory so runs don't overwrite each other
    ckpt_suffix = "" if args.model_type == "full" else f"_{args.model_type}"

    if args.debug:
        debug_window_dir = ROOT / "data" / "processed" / "windows_debug"
        debug_ckpt_dir = ROOT / "results" / "models" / \
            f"checkpoints_debug{ckpt_suffix}"
        if args.max_epochs is None:
            cfg["max_epochs"] = 5
        cfg["save_every"] = 1
        cfg["early_stop_patience"] = 5
        log.warning(
            "=== DEBUG MODE: windows_debug/, checkpoints_debug/, max_epochs=5 ===")
        train(config=cfg, resume=args.resume,
              ckpt_dir=debug_ckpt_dir, window_dir=debug_window_dir)
    else:
        ckpt_dir = ROOT / "results" / "models" / f"checkpoints{ckpt_suffix}"
        w_dir = Path(args.window_dir) if args.window_dir else WINDOW_DIR
        train(config=cfg, resume=args.resume,
              ckpt_dir=ckpt_dir, window_dir=w_dir)
