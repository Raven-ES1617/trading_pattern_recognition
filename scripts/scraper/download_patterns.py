from __future__ import annotations

import argparse
import hashlib
import http.client
import mimetypes
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from .bing_images import USER_AGENT, search_image_urls
    from .patterns import PATTERN_MAP, PATTERNS, PatternSpec
except ImportError:
    from bing_images import USER_AGENT, search_image_urls
    from patterns import PATTERN_MAP, PATTERNS, PatternSpec


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "raw"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"}
RASTER_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SKIPPED_CONTENT_TYPES = {"image/gif", "image/svg+xml"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download chart pattern images into data/raw/<pattern_name>."
    )
    parser.add_argument(
        "--per-pattern",
        type=int,
        default=10,
        help="How many images to keep per pattern folder.",
    )
    parser.add_argument(
        "--patterns",
        nargs="*",
        choices=sorted(PATTERN_MAP),
        help="Optional subset of pattern folders to refresh.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Base directory for raw images.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore existing files and redownload up to the target count.",
    )
    parser.add_argument(
        "--pages-per-query",
        type=int,
        default=8,
        help="How many Bing result pages to scan for each search phrase.",
    )
    parser.add_argument(
        "--candidate-multiplier",
        type=int,
        default=3,
        help="How many candidate URLs to request relative to the remaining target.",
    )
    return parser.parse_args()


def get_target_patterns(selected: list[str] | None) -> list[PatternSpec]:
    if not selected:
        return PATTERNS
    return [PATTERN_MAP[name] for name in selected]


def existing_image_count(pattern_dir: Path) -> int:
    return sum(
        1
        for item in pattern_dir.iterdir()
        if item.is_file() and item.suffix.lower() in RASTER_SUFFIXES
    )


def clear_existing_images(pattern_dir: Path) -> None:
    for item in pattern_dir.iterdir():
        if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES:
            item.unlink()


def guess_extension(image_url: str, content_type: str | None) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            if guessed == ".jpe":
                return ".jpg"
            return guessed

    parsed = urllib.parse.urlparse(image_url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in RASTER_SUFFIXES:
        return suffix
    return ".jpg"


def normalize_image_url(image_url: str) -> str:
    parsed = urllib.parse.urlsplit(image_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("unsupported image url")

    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            urllib.parse.quote(parsed.path, safe="/:%._-~!$&'()*+,;=@"),
            urllib.parse.quote_plus(parsed.query, safe="=&:%._-~!$'()*+,;@/?"),
            urllib.parse.quote(parsed.fragment, safe=""),
        )
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_hashes(pattern_dir: Path) -> set[str]:
    hashes: set[str] = set()
    for item in pattern_dir.iterdir():
        if item.is_file() and item.suffix.lower() in RASTER_SUFFIXES:
            hashes.add(file_sha256(item))
    return hashes


def next_serial(pattern_dir: Path) -> int:
    serials: list[int] = []
    for item in pattern_dir.iterdir():
        if not item.is_file():
            continue
        stem_parts = item.stem.rsplit("_", maxsplit=1)
        if len(stem_parts) != 2 or not stem_parts[1].isdigit():
            continue
        serials.append(int(stem_parts[1]))
    return max(serials, default=0) + 1


def download_image(image_url: str, destination: Path, known_hashes: set[str], retries: int = 3) -> bool:
    try:
        normalized_url = normalize_image_url(image_url)
    except ValueError:
        return False

    request = urllib.request.Request(
        normalized_url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://www.bing.com/",
        },
    )

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content_type = response.headers.get("Content-Type", "")
                mime_type = content_type.split(";", maxsplit=1)[0].strip().lower()
                if not mime_type.startswith("image/") or mime_type in SKIPPED_CONTENT_TYPES:
                    return False

                extension = guess_extension(normalized_url, content_type)
                final_path = destination.with_suffix(extension)
                payload = response.read()
                if not payload:
                    return False
                payload_hash = hashlib.sha256(payload).hexdigest()
                if payload_hash in known_hashes:
                    return False
                final_path.write_bytes(payload)
                known_hashes.add(payload_hash)
                return True
        except (
            TimeoutError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            ValueError,
            http.client.InvalidURL,
            http.client.RemoteDisconnected,
            OSError,
        ):
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
    return False


def ensure_pattern_dirs(patterns: list[PatternSpec], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for pattern in patterns:
        (output_dir / pattern.folder).mkdir(parents=True, exist_ok=True)


def candidate_limit(remaining: int, multiplier: int) -> int:
    return max(remaining * max(multiplier, 1), 120)


def download_for_pattern(
    pattern: PatternSpec,
    output_dir: Path,
    per_pattern: int,
    force: bool,
    pages_per_query: int,
    candidate_multiplier: int,
) -> tuple[int, int]:
    pattern_dir = output_dir / pattern.folder
    if force:
        clear_existing_images(pattern_dir)
    present = 0 if force else existing_image_count(pattern_dir)
    remaining = per_pattern - present
    if remaining <= 0:
        return 0, present

    downloaded = 0
    serial = next_serial(pattern_dir)
    known_hashes = existing_hashes(pattern_dir)
    seen_urls: set[str] = set()

    for query in pattern.queries:
        query_remaining = per_pattern - existing_image_count(pattern_dir)
        if query_remaining <= 0:
            break

        candidates = search_image_urls(
            query,
            limit=candidate_limit(query_remaining, candidate_multiplier),
            pages=pages_per_query,
        )
        for image_url in candidates:
            if image_url in seen_urls:
                continue
            seen_urls.add(image_url)

            target_path = pattern_dir / f"{pattern.folder}_{serial:04d}"
            if download_image(
                image_url=image_url,
                destination=target_path,
                known_hashes=known_hashes,
            ):
                downloaded += 1
                serial += 1
                if downloaded >= remaining:
                    break
        if downloaded >= remaining:
            break

    return downloaded, present + downloaded


def main() -> int:
    args = parse_args()
    patterns = get_target_patterns(args.patterns)
    ensure_pattern_dirs(patterns=patterns, output_dir=args.output_dir)

    for pattern in patterns:
        downloaded, total = download_for_pattern(
            pattern=pattern,
            output_dir=args.output_dir,
            per_pattern=args.per_pattern,
            force=args.force,
            pages_per_query=args.pages_per_query,
            candidate_multiplier=args.candidate_multiplier,
        )
        print(
            f"{pattern.folder}: downloaded={downloaded}, total_files={total}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
