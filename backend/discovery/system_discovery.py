
import os
import ctypes
from pathlib import Path
from ctypes import wintypes


# Windows drive types
DRIVE_FIXED = 3


def discover_fixed_drives():
    """
    Discover all available fixed drives on the computer.

    Returns:
        A list of Path objects representing fixed drives.
    """

    # Handle non-Windows operating systems
    if os.name != "nt":
        return [Path("/")]

    # Access the Windows system library
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # Get the list of available logical drives
    get_logical_drives = kernel32.GetLogicalDrives
    get_logical_drives.restype = wintypes.DWORD

    # Get the type of a particular drive
    get_drive_type = kernel32.GetDriveTypeW
    get_drive_type.argtypes = [wintypes.LPCWSTR]
    get_drive_type.restype = wintypes.UINT

    # Retrieve the drive information as a bitmask
    drive_mask = get_logical_drives()

    # Store discovered fixed drives
    fixed_drives = []

    # Windows supports drive letters A to Z
    for index in range(26):

        # Check whether this drive letter exists
        if drive_mask & (1 << index):

            # Convert index into a drive letter
            drive_letter = chr(ord("A") + index)

            # Construct the drive path
            drive_path = f"{drive_letter}:\\"

            # Identify the drive type
            drive_type = get_drive_type(drive_path)

            # Include only fixed drives
            if drive_type == DRIVE_FIXED:
                fixed_drives.append(Path(drive_path))

    return fixed_drives


if __name__ == "__main__":

    drives = discover_fixed_drives()

    print("\nLENS - System Drive Discovery")
    print("-" * 40)

    if not drives:
        print("No fixed drives found.")

    for drive in drives:
        print(f"Discovered drive: {drive}")
