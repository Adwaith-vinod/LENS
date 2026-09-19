from pathlib import Path

path = Path("C:/Users/adwai/OneDrive/Documents")

supported_extension = {".pdf",".txt",".docx"}
for item in path.rglob("*"):
    if item.is_file():
         if item.suffix.lower() in supported_extension:
            print("Name:", item.name)
            print("Path:", item)
            print("Extension:", item.suffix)
            print("Size:", item.stat().st_size, "bytes")
            print("Parent:", item.parent)
            print("-" * 40)