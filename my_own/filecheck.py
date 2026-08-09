from .errors import FileCheckError, ParsingError
from pathlib import Path
from typing import List



class FileCheck:
    """Validate the program arguments and
    ensure the map file exists and is readable."""

    @classmethod
    def _validate_args(cls, args: List[str]) -> None:
        """Check the number of arguments provided."""

        if len(args) != 2:
            raise ParsingError("Invalid number of arguments provided.")
        map_path: Path = Path(args[1])
        if not map_path.exists():
            raise FileCheckError("The file was not found.")
        try:
            with map_path.open("r"):
                pass
        except OSError as exc:
            raise FileCheckError(f"Cannot open file: {exc}") from exc

    @classmethod
    def validate_map(cls, args: List[str]) -> None:
        """Ensure the command line is valid."""

        cls._validate_args(args)
