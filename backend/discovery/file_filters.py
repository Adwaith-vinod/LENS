
from pathlib import Path
import stat


# Supported file extensions grouped by category
SUPPORTED_FILE_TYPES = {

    "documents": {
        ".pdf", ".docx", ".doc", ".txt",
        ".rtf", ".odt", ".md"
    },

    "presentations": {
        ".pptx", ".ppt", ".odp"
    },

    "spreadsheets": {
        ".xlsx", ".xls", ".csv", ".ods"
    },

    "structured_data": {
        ".json", ".xml"
    },

    "images": {
        ".jpg", ".jpeg", ".png", ".webp",
        ".bmp", ".tif", ".tiff", ".gif"
    }
}


# Combine all supported extensions into one set
SUPPORTED_EXTENSIONS = set().union(
    *SUPPORTED_FILE_TYPES.values()
)


# Directories that LENS should not scan
EXCLUDED_DIRECTORY_NAMES = {

    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "$recycle.bin",
    "system volume information",
    "appdata",

    "node_modules",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "site-packages",

    "cache",
    "caches",
    "temp",
    "tmp",

    "dataset",
    "datasets",
    "dist",
    "build",
    ".pytest_cache",
    ".vscode"
}


# Maximum allowed file size: 100 MB
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


def is_hidden(path):
    """
    Check whether a file or directory is hidden.
    """

    path = Path(path)

    # Unix-style hidden names
    if path.name.startswith("."):
        return True

    try:
        # Windows hidden attribute
        attributes = path.stat().st_file_attributes

        return bool(
            attributes & getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0x2)
        )

    except (OSError, AttributeError):
        return False


def should_skip_directory(directory_path):
    """
    Determine whether a directory should be excluded.
    """

    directory_path = Path(directory_path)

    directory_name = directory_path.name.lower()

    if directory_name in EXCLUDED_DIRECTORY_NAMES:
        return True

    if is_hidden(directory_path):
        return True

    return False


def get_file_category(file_path):
    """
    Identify the category of a file based on its extension.
    """

    extension = Path(file_path).suffix.lower()

    for category, extensions in SUPPORTED_FILE_TYPES.items():

        if extension in extensions:
            return category

    return None


def is_supported_file(file_path):
    """
    Check whether a file is eligible for initial indexing.
    """

    file_path = Path(file_path)

    try:

        # Ignore symbolic links
        if file_path.is_symlink():
            return False

        # Check whether the file exists
        if not file_path.is_file():
            return False

        # Check supported extensions
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return False

        # Ignore hidden files
        if is_hidden(file_path):
            return False

        # Check file size
        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            return False

        return True

    except OSError:
        # Ignore files that cannot be accessed
        return False


if __name__ == "__main__":

    print("LENS Supported Extensions")
    print("-" * 40)

    for category, extensions in SUPPORTED_FILE_TYPES.items():

        print(f"\n{category.upper()}")

        for extension in sorted(extensions):
            print(extension)

    print("\nTotal supported extensions:", len(SUPPORTED_EXTENSIONS))
