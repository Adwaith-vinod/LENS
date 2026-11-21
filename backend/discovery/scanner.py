
import os
import stat
import logging

from pathlib import Path
from datetime import datetime
from collections import Counter

from backend.discovery.file_filters import (
    is_supported_file,
    should_skip_directory,
    get_file_category
)


logger = logging.getLogger(__name__)


def is_reparse_directory(directory_path):
    """
    Detect Windows junctions and other filesystem reparse directories.

    These can point outside the current directory tree or create
    unexpected scanning loops.
    """

    try:
        path_stat = Path(directory_path).lstat()

        reparse_flag = getattr(
            stat,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            0x400
        )

        return bool(
            getattr(path_stat, "st_file_attributes", 0)
            & reparse_flag
        )

    except OSError:
        return True


def get_file_metadata(file_path):
    """
    Collect metadata required for file discovery and retrieval.
    """

    path = Path(file_path)

    try:
        file_stat = path.stat()

        return {
            "file_name": path.name,
            "file_path": str(path.resolve()),
            "extension": path.suffix.lower(),
            "category": get_file_category(path),
            "file_size_bytes": file_stat.st_size,
            "modified_at": datetime.fromtimestamp(
                file_stat.st_mtime
            ).astimezone().isoformat()
        }

    except OSError as error:
        logger.warning(
            "Could not read metadata for %s: %s",
            path,
            error
        )

        return None


def scan_directory(folder_path):
    """
    Recursively scan a directory for supported files.

    Returns:
        A list of dictionaries containing discovered file metadata.
    """

    root = Path(folder_path).expanduser()

    if not root.exists():
        raise FileNotFoundError(
            f"Directory does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Not a directory: {root}"
        )

    discovered_files = []

    # Use an iterative traversal instead of recursive function calls.
    directories_to_scan = [root]

    while directories_to_scan:

        current_directory = directories_to_scan.pop()

        try:
            with os.scandir(current_directory) as entries:

                for entry in entries:

                    entry_path = Path(entry.path)

                    try:

                        # Never follow symbolic links.
                        if entry.is_symlink():
                            continue

                        # Handle directories first.
                        if entry.is_dir(follow_symlinks=False):

                            if should_skip_directory(entry_path):
                                continue

                            if is_reparse_directory(entry_path):
                                continue

                            directories_to_scan.append(entry_path)
                            continue

                        # Ignore anything that is not a regular file.
                        if not entry.is_file(follow_symlinks=False):
                            continue

                        # Apply the file eligibility rules.
                        if not is_supported_file(entry_path):
                            continue

                        # Collect metadata.
                        metadata = get_file_metadata(entry_path)

                        if metadata is not None:
                            discovered_files.append(metadata)

                    except OSError as error:
                        logger.warning(
                            "Could not inspect %s: %s",
                            entry_path,
                            error
                        )

        except OSError as error:
            logger.warning(
                "Could not access directory %s: %s",
                current_directory,
                error
            )

    return discovered_files


def scan_directories(folder_paths):
    """
    Scan multiple directories and avoid duplicate file paths.
    """

    all_files = []
    discovered_paths = set()

    for folder_path in folder_paths:

        try:
            files = scan_directory(folder_path)

            for file_info in files:

                normalized_path = os.path.normcase(
                    os.path.normpath(file_info["file_path"])
                )

                if normalized_path in discovered_paths:
                    continue

                discovered_paths.add(normalized_path)
                all_files.append(file_info)

        except (OSError, ValueError) as error:
            logger.warning(
                "Skipping scan root %s: %s",
                folder_path,
                error
            )

    return all_files


def print_scan_summary(discovered_files):
    """
    Display a summary of the discovered files.
    """

    category_counts = Counter(
        file_info["category"]
        for file_info in discovered_files
    )

    print("\nLENS - File Discovery Summary")
    print("=" * 45)

    print(f"Total files discovered: {len(discovered_files)}")

    print("\nFiles by category:")

    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count}")

    print("\nDiscovered files:")

    for file_info in discovered_files:

        print(f"\nName: {file_info['file_name']}")
        print(f"Location: {file_info['file_path']}")
        print(f"Category: {file_info['category']}")
        print(f"Size: {file_info['file_size_bytes']} bytes")


if __name__ == "__main__":

    logging.basicConfig(level=logging.WARNING)

    folder = input(
        "Enter a folder path to test LENS scanner: "
    ).strip().strip('"')

    try:
        files = scan_directory(folder)
        print_scan_summary(files)

    except (FileNotFoundError, NotADirectoryError) as error:
        print(f"\nScan error: {error}")
