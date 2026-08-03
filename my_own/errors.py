class ParsingError(Exception):
    """General parsing error."""

class FileCheckError(ParsingError):
    """Raise an error if the file does not exist or cannot be accessed."""