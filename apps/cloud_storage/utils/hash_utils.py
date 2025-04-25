import hashlib
import time


def generate_unique_hash(filename: str) -> str:
    """
    Generate a unique SHA-256 hash for a given filename using timestamp.
    """
    timestamp = str(time.time_ns())
    unique_input = f"{filename}-{timestamp}"
    hash_object = hashlib.sha256(unique_input.encode('utf-8'))
    file_extension = filename.split(".")[-1]
    return f"{hash_object.hexdigest()}.{file_extension}"
