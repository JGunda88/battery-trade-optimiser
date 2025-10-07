"""
Utility functions for validating input files and preparing output paths.
"""

from pathlib import Path
from utils.custom_exceptions import InputFileMissing, InvalidFileType, OutputPathError
VALID_XLS = {".xls", ".xlsx"}

class FileChecker:
    """
    This class contains methods to check the validity of input Excel files and prepare output paths.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath

    def validate_excel_file(self) -> Path:
        """
        Validate that the given path exists and points to an Excel file.
        Steps:
          1) Expand user, resolve to absolute path.
          2) Ensure the file exists and is a file.
          3) Ensure extension is .xls or .xlsx.
        Raises:
            InputFileMissing: If the path does not exist or is not a file.
            InvalidFileType: If the extension is not an Excel type.
        Returns:
            Path: Resolved path to the valid Excel file.
        """
        p = Path(self.filepath).expanduser().resolve()
        if not p.exists() or not p.is_file():
            raise InputFileMissing(str(p))
        if p.suffix.lower() not in VALID_XLS:
            raise InvalidFileType(str(p), "Excel .xls or .xlsx")
        return p

    def prepare_output_path(self) -> Path:
        """
        Prepare the output file path by ensuring the parent directory exists.
        Steps:
          1) Expand user and resolve to absolute path.
          2) Create parent directory if needed.
        Raises:
            OutputPathError: If the parent directory cannot be created.
        Returns:
            Path: Resolved path for the output file.
        """
        p = Path(self.filepath).expanduser().resolve()
        try:
            parent = p.parent
            if parent.exists() and not parent.is_dir():
                # Parent exists but is a file, not a directory
                raise OutputPathError(f"Parent exists and is not a directory: {parent}")
            parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise OutputPathError(str(e))
        return p
