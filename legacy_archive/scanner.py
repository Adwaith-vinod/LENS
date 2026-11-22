from pathlib  import Path

SUPORTED_EXTENSION = {".pdf", ".docx", ".txt"}

def scan_directory(folder_path):
    folder = Path(folder_path)
    files = []

    for items in folder.rglob("*"):
        if items.is_file() and items.suffix.lower() in SUPORTED_EXTENSION:
            files.append(items)

    return files


if __name__ == "__main__":

    files = scan_directory("C:/Users/adwai/Documents")

    for file in files:
        print(file)
