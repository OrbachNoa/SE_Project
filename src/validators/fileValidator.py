# region Imports
import os
# endregion

def validate_language(file_path):
    """
    Validates that the file is UTF-8
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read()

    except UnicodeDecodeError:
        raise ValueError(f"{file_path} is not a valid UTF-8 file.")

    except OSError as e:
        raise ValueError(f"Cannot read file {file_path}: {e}")
    
def validate_file_exists(file_path):
    """
    Validates that the file exists and is readable
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Missing or invalid file: {file_path}")

def validate_file_not_empty(file_path):
    """
    Validates that the file is not empty
    """
    if os.path.getsize(file_path) == 0:
        raise ValueError(f"{file_path} file is empty.")

def validate_all_files(file_paths):
    """
    Check if all files exist, are not empty, and are in English.
    """
    for file_path in file_paths:
        validate_file_exists(file_path)
        validate_file_not_empty(file_path)
        validate_language(file_path)