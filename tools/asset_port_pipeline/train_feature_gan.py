from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class Generator(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(dim, 128),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(128, 128),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(128, dim),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.model(values)


class Discriminator(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(dim, 128),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(128, 64),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(64, 1),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.model(values)


def load_dataset(dataset_path: Path) -> Tuple[torch.Tensor, torch.Tensor]:
    positives: List[List[float]] = []
    negatives: List[List[float]] = []

    with dataset_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            features = [float(value) for value in row["features"]]
            if int(row["label"]) == 1:
                positives.append(features)
            else:
                negatives.append(features)

    if not positives:
        raise RuntimeError("Dataset has no positive samples (label=1)")
    if not negatives:
        raise RuntimeError("Dataset has no negative samples (label=0)")

    return torch.tensor(positives, dtype=torch.float32), torch.tensor(negatives, dtype=torch.float32)


def normalize(values: torch.Tensor, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
    return (values - mean) / std


def denormalize(values: torch.Tensor, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
    return values * std + mean


def main() -> None:
    parser = argparse.ArgumentParser(description="Train feature-space adversarial model for BO3->BO2 coercion.")
    parser.add_argument(
        "--dataset",
        default="_build/asset_port_pipeline/dataset/dataset.jsonl",
        help="Path to dataset.jsonl from build_feature_dataset.py",
    )
    parser.add_argument(
        "--meta",
        default="_build/asset_port_pipeline/dataset/dataset_meta.json",
        help="Path to dataset_meta.json",
    )
    parser.add_argument("--epochs", type=int, default=200, help="Training epochs.")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size.")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate.")
    parser.add_argument("--lambda-recon", type=float, default=10.0, help="Generator reconstruction weight.")
    parser.add_argument("--device", default="auto", help="cuda, cpu, or auto")
    parser.add_argument(
        "--output-dir",
        default="_build/asset_port_pipeline/models",
        help="Directory for checkpoints and metrics.",
    )
    parser.add_argument("--seed", type=int, default=1337, help="Random seed.")
    args = parser.parse_args()

    torch.manual_seed(args.seed)

    dataset_path = Path(args.dataset).resolve()
    meta_path = Path(args.meta).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Dataset meta not found: {meta_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    mean = torch.tensor(meta["normalization"]["mean"], dtype=torch.float32)
    std = torch.tensor(meta["normalization"]["std"], dtype=torch.float32)
    feature_names = meta["feature_names"]
    dim = len(feature_names)

    pos, neg = load_dataset(dataset_path)
    if pos.size(1) != dim or neg.size(1) != dim:
        raise RuntimeError("Feature dimension mismatch between dataset and meta")

    device = torch.device("cuda" if (args.device == "auto" and torch.cuda.is_available()) else args.device)
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    mean = mean.to(device)
    std = std.to(device)
    pos = normalize(pos.to(device), mean, std)
    neg = normalize(neg.to(device), mean, std)

    pos_loader = DataLoader(TensorDataset(pos), batch_size=args.batch_size, shuffle=True, drop_last=True)
    neg_loader = DataLoader(TensorDataset(neg), batch_size=args.batch_size, shuffle=True, drop_last=True)

    if len(pos_loader) == 0 or len(neg_loader) == 0:
        raise RuntimeError("Insufficient dataset size for requested batch-size")

    generator = Generator(dim).to(device)
    discriminator = Discriminator(dim).to(device)

    bce = nn.BCEWithLogitsLoss()
    l1 = nn.L1Loss()
    opt_g = torch.optim.Adam(generator.parameters(), lr=args.lr, betas=(0.5, 0.999))
    opt_d = torch.optim.Adam(discriminator.parameters(), lr=args.lr, betas=(0.5, 0.999))

    metrics: Dict[str, List[float]] = {
        "d_loss": [],
        "g_loss": [],
        "g_adv_loss": [],
        "g_recon_loss": [],
    }

    for epoch in range(1, args.epochs + 1):
        epoch_d = 0.0
        epoch_g = 0.0
        epoch_g_adv = 0.0
        epoch_g_recon = 0.0
        steps = min(len(pos_loader), len(neg_loader))

        pos_iter = iter(pos_loader)
        neg_iter = iter(neg_loader)

        for _ in range(steps):
            real = next(pos_iter)[0]
            source = next(neg_iter)[0]
            batch_size = real.size(0)

            # Train discriminator
            opt_d.zero_grad(set_to_none=True)
            with torch.no_grad():
                fake = generator(source)
            pred_real = discriminator(real)
            pred_fake = discriminator(fake)
            loss_d = bce(pred_real, torch.ones((batch_size, 1), device=device)) + bce(
                pred_fake, torch.zeros((batch_size, 1), device=device)
            )
            loss_d.backward()
            opt_d.step()

            # Train generator
            opt_g.zero_grad(set_to_none=True)
            fake = generator(source)
            pred_fake_for_g = discriminator(fake)
            loss_adv = bce(pred_fake_for_g, torch.ones((batch_size, 1), device=device))
            loss_recon = l1(fake, source)
            loss_g = loss_adv + args.lambda_recon * loss_recon
            loss_g.backward()
            opt_g.step()

            epoch_d += float(loss_d.item())
            epoch_g += float(loss_g.item())
            epoch_g_adv += float(loss_adv.item())
            epoch_g_recon += float(loss_recon.item())

        metrics["d_loss"].append(epoch_d / steps)
        metrics["g_loss"].append(epoch_g / steps)
        metrics["g_adv_loss"].append(epoch_g_adv / steps)
        metrics["g_recon_loss"].append(epoch_g_recon / steps)

        if epoch % max(1, args.epochs // 20) == 0 or epoch == 1:
            print(
                f"epoch={epoch:04d} "
                f"d_loss={metrics['d_loss'][-1]:.4f} "
                f"g_loss={metrics['g_loss'][-1]:.4f} "
                f"g_adv={metrics['g_adv_loss'][-1]:.4f} "
                f"g_recon={metrics['g_recon_loss'][-1]:.4f}"
            )

    torch.save(generator.state_dict(), output_dir / "generator.pt")
    torch.save(discriminator.state_dict(), output_dir / "discriminator.pt")

    with torch.no_grad():
        sample_input = neg[: min(32, neg.size(0))]
        converted = denormalize(generator(sample_input), mean, std).cpu().tolist()
    sample_payload = {"feature_names": feature_names, "converted_feature_samples": converted}
    (output_dir / "converted_feature_samples.json").write_text(
        json.dumps(sample_payload, indent=2), encoding="utf-8"
    )

    (output_dir / "train_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Saved checkpoints and metrics to: {output_dir}")


if __name__ == "__main__":
    main()

