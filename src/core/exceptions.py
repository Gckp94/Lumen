"""Custom exceptions for Lumen application."""


class LumenError(Exception):
    """Base exception for Lumen application.

    All custom exceptions in the application should inherit from this class
    to enable consistent exception handling.
    """


class FileLoadError(LumenError):
    """Raised when file loading fails.

    This exception is raised when a file cannot be read, parsed,
    or is in an unsupported format.
    """


class ColumnMappingError(LumenError):
    """Raised when column mapping is invalid.

    This exception is raised when required columns cannot be mapped
    or when the mapping configuration is inconsistent.
    """


class CacheError(LumenError):
    """Raised when cache operations fail.

    This exception is raised when cache read/write operations fail,
    but should generally be caught internally as caching is non-critical.
    """


class ExportError(LumenError):
    """Raised when export operations fail.

    This exception is raised when data export fails due to permission
    errors, disk full, or other I/O issues.
    """


class EquityCalculationError(LumenError):
    """Raised when equity curve calculation fails.

    This exception is raised when equity curve calculation encounters
    invalid data, missing columns, or other calculation errors.
    """
