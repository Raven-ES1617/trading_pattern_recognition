from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import warnings
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = ROOT_DIR / "data" / "raw"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "processed" / "clean"
DEFAULT_QUARANTINE_DIR = ROOT_DIR / "data" / "quarantine"
DEFAULT_REPORT_DIR = ROOT_DIR / "data" / "reports"
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


@dataclass
class ImageDecision:
    source_path: str
    label: str
    action: str
    reason: str
    output_path: str | None = None
    duplicate_of: str | None = None
    image_format: str | None = None
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    dhash: str | None = None
    entropy: float | None = None
    edge_density: float | None = None
    frame_count: int | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean raw chart pattern images and build a training-ready dataset."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--quarantine-dir", type=Path, default=DEFAULT_QUARANTINE_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--min-side", type=int, default=160)
    parser.add_argument("--min-aspect-ratio", type=float, default=0.45)
    parser.add_argument("--max-aspect-ratio", type=float, default=2.50)
    parser.add_argument("--min-entropy", type=float, default=0.35)
    parser.add_argument("--min-edge-density", type=float, default=0.01)
    parser.add_argument("--dedupe-distance", type=int, default=4)
    parser.add_argument(
        "--reset-output",
        action="store_true",
        help="Delete existing processed, quarantine, and report outputs before running.",
    )
    return parser.parse_args()


def iter_source_files(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob("*") if path.is_file())


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def flatten_to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in {"RGBA", "LA"}:
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, image.convert("RGBA")).convert("RGB")
    if image.mode == "P":
        return image.convert("RGBA").convert("RGB")
    return image.convert("RGB")


def difference_hash(image: Image.Image, size: int = 8) -> int:
    grayscale = image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    result = 0
    for y in range(size):
        for x in range(size):
            result <<= 1
            left = grayscale.getpixel((x, y))
            right = grayscale.getpixel((x + 1, y))
            if left > right:
                result |= 1
    return result


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def format_hash(value: int) -> str:
    return f"{value:016x}"


def relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def copy_to_quarantine(source_path: Path, quarantine_dir: Path, reason: str, label: str) -> Path:
    target_dir = quarantine_dir / reason / label
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / source_path.name
    if target_path.exists():
        target_path = target_dir / f"{source_path.stem}_{hashlib.md5(str(source_path).encode('utf-8')).hexdigest()[:8]}{source_path.suffix}"
    shutil.copy2(source_path, target_path)
    return target_path


def save_clean_image(image: Image.Image, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(target_path, format="PNG", optimize=True)


def analyze_image(source_path: Path) -> tuple[dict[str, float | int | str], Image.Image]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with Image.open(source_path) as image:
            frame_count = getattr(image, "n_frames", 1)
            image.load()
            rgb_image = flatten_to_rgb(image)

    width, height = rgb_image.size
    gray_image = rgb_image.convert("L")
    entropy = float(gray_image.entropy())
    edge_density = float(ImageStat.Stat(gray_image.filter(ImageFilter.FIND_EDGES)).mean[0] / 255.0)
    dhash = difference_hash(rgb_image)

    metadata: dict[str, float | int | str] = {
        "image_format": rgb_image.format or source_path.suffix.lower().lstrip("."),
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "entropy": entropy,
        "edge_density": edge_density,
        "dhash": dhash,
    }
    return metadata, rgb_image


def decision_for_rejection(
    source_path: Path,
    label: str,
    reason: str,
    quarantine_dir: Path,
    metadata: dict[str, float | int | str] | None = None,
    duplicate_of: str | None = None,
) -> ImageDecision:
    quarantine_path = copy_to_quarantine(source_path, quarantine_dir, reason, label)
    decision = ImageDecision(
        source_path=relative_to_root(source_path),
        label=label,
        action="quarantine",
        reason=reason,
        output_path=relative_to_root(quarantine_path),
        duplicate_of=duplicate_of,
    )
    if metadata:
        decision.image_format = str(metadata.get("image_format")) if metadata.get("image_format") is not None else None
        decision.width = int(metadata["width"]) if metadata.get("width") is not None else None
        decision.height = int(metadata["height"]) if metadata.get("height") is not None else None
        decision.frame_count = int(metadata["frame_count"]) if metadata.get("frame_count") is not None else None
        decision.entropy = float(metadata["entropy"]) if metadata.get("entropy") is not None else None
        decision.edge_density = float(metadata["edge_density"]) if metadata.get("edge_density") is not None else None
        decision.dhash = format_hash(int(metadata["dhash"])) if metadata.get("dhash") is not None else None
    return decision


def write_reports(
    decisions: list[ImageDecision],
    report_dir: Path,
    kept_counts: Counter[str],
    quarantined_counts: Counter[str],
) -> None:
    ensure_dir(report_dir)

    report_path = report_dir / "cleaning_report.csv"
    with report_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=list(asdict(decisions[0]).keys()) if decisions else list(ImageDecision.__dataclass_fields__.keys()))
        writer.writeheader()
        for decision in decisions:
            writer.writerow(asdict(decision))

    reason_counts = Counter(decision.reason for decision in decisions if decision.action == "quarantine")
    summary = {
        "input_files": len(decisions),
        "kept_files": sum(kept_counts.values()),
        "quarantined_files": sum(quarantined_counts.values()),
        "kept_per_label": dict(sorted(kept_counts.items())),
        "quarantined_per_label": dict(sorted(quarantined_counts.items())),
        "quarantine_reasons": dict(sorted(reason_counts.items())),
    }
    (report_dir / "cleaning_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    hash_groups: dict[str, list[ImageDecision]] = defaultdict(list)
    for decision in decisions:
        if decision.sha256:
            hash_groups[decision.sha256].append(decision)

    cross_label_conflicts = [
        {
            "sha256": sha256,
            "labels": sorted({entry.label for entry in entries}),
            "sources": [entry.source_path for entry in entries],
        }
        for sha256, entries in hash_groups.items()
        if len({entry.label for entry in entries}) > 1
    ]
    (report_dir / "cross_label_duplicates.json").write_text(
        json.dumps(cross_label_conflicts, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()

    if args.reset_output:
        ensure_clean_dir(args.output_dir)
        ensure_clean_dir(args.quarantine_dir)
        ensure_clean_dir(args.report_dir)
    else:
        ensure_dir(args.output_dir)
        ensure_dir(args.quarantine_dir)
        ensure_dir(args.report_dir)

    source_files = iter_source_files(args.input_dir)
    kept_counts: Counter[str] = Counter()
    quarantined_counts: Counter[str] = Counter()
    decisions: list[ImageDecision] = []
    seen_sha: dict[str, Path] = {}
    seen_hashes_by_label: dict[str, list[tuple[int, Path]]] = defaultdict(list)

    for source_path in source_files:
        label = source_path.parent.name
        suffix = source_path.suffix.lower()

        if suffix not in SUPPORTED_SUFFIXES:
            decision = decision_for_rejection(
                source_path=source_path,
                label=label,
                reason="unsupported_suffix",
                quarantine_dir=args.quarantine_dir,
            )
            decisions.append(decision)
            quarantined_counts[label] += 1
            continue

        sha256 = file_sha256(source_path)
        duplicate_of = seen_sha.get(sha256)
        if duplicate_of is not None:
            reason = "exact_duplicate_cross_label" if duplicate_of.parent.name != label else "exact_duplicate"
            decision = decision_for_rejection(
                source_path=source_path,
                label=label,
                reason=reason,
                quarantine_dir=args.quarantine_dir,
                duplicate_of=relative_to_root(duplicate_of),
            )
            decision.sha256 = sha256
            decisions.append(decision)
            quarantined_counts[label] += 1
            continue

        try:
            metadata, rgb_image = analyze_image(source_path)
        except (UnidentifiedImageError, OSError, ValueError):
            decision = decision_for_rejection(
                source_path=source_path,
                label=label,
                reason="unreadable_image",
                quarantine_dir=args.quarantine_dir,
            )
            decision.sha256 = sha256
            decisions.append(decision)
            quarantined_counts[label] += 1
            continue

        metadata["sha256"] = sha256
        aspect_ratio = float(metadata["width"]) / float(metadata["height"])

        rejection_reason: str | None = None
        if int(metadata["frame_count"]) > 1:
            rejection_reason = "animated_image"
        elif min(int(metadata["width"]), int(metadata["height"])) < args.min_side:
            rejection_reason = "too_small"
        elif aspect_ratio < args.min_aspect_ratio or aspect_ratio > args.max_aspect_ratio:
            rejection_reason = "bad_aspect_ratio"
        elif float(metadata["entropy"]) < args.min_entropy and float(metadata["edge_density"]) < args.min_edge_density:
            rejection_reason = "low_information"
        else:
            for existing_hash, existing_path in seen_hashes_by_label[label]:
                if hamming_distance(int(metadata["dhash"]), existing_hash) <= args.dedupe_distance:
                    rejection_reason = "perceptual_duplicate"
                    duplicate_of = relative_to_root(existing_path)
                    break

        if rejection_reason:
            decision = decision_for_rejection(
                source_path=source_path,
                label=label,
                reason=rejection_reason,
                quarantine_dir=args.quarantine_dir,
                metadata=metadata,
                duplicate_of=duplicate_of,
            )
            decision.sha256 = sha256
            decisions.append(decision)
            quarantined_counts[label] += 1
            continue

        seen_sha[sha256] = source_path
        seen_hashes_by_label[label].append((int(metadata["dhash"]), source_path))

        kept_counts[label] += 1
        clean_name = f"{label}_{kept_counts[label]:04d}.png"
        clean_path = args.output_dir / label / clean_name
        save_clean_image(rgb_image, clean_path)
        decision = ImageDecision(
            source_path=relative_to_root(source_path),
            label=label,
            action="keep",
            reason="kept",
            output_path=relative_to_root(clean_path),
            image_format=str(metadata["image_format"]),
            width=int(metadata["width"]),
            height=int(metadata["height"]),
            sha256=sha256,
            dhash=format_hash(int(metadata["dhash"])),
            entropy=float(metadata["entropy"]),
            edge_density=float(metadata["edge_density"]),
            frame_count=int(metadata["frame_count"]),
        )
        decisions.append(decision)

    write_reports(
        decisions=decisions,
        report_dir=args.report_dir,
        kept_counts=kept_counts,
        quarantined_counts=quarantined_counts,
    )

    print(f"input_files={len(source_files)}")
    print(f"kept_files={sum(kept_counts.values())}")
    print(f"quarantined_files={sum(quarantined_counts.values())}")
    for label in sorted(set(kept_counts) | set(quarantined_counts)):
        print(
            f"{label}: kept={kept_counts[label]}, quarantined={quarantined_counts[label]}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
