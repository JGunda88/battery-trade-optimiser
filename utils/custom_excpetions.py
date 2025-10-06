"""
Custom exceptions for file handling operations and any other exceptions raised in this application.
"""

class InputFileMissing(Exception):
    def __init__(self, path: str):
        super().__init__(f"File not found: {path}")

class InvalidFileType(Exception):
    def __init__(self, path: str, expected: str):
        super().__init__(f"Invalid file type for {path}. Expected {expected}")

class OutputPathError(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Cannot prepare output path. {reason}")