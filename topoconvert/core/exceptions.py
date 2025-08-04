"""Custom exceptions for TopoConvert."""


class TopoConvertError(Exception):
    """Base exception for all TopoConvert errors."""
    pass


class FileFormatError(TopoConvertError):
    """Raised when file format is invalid or unsupported."""
    pass


class ProcessingError(TopoConvertError):
    """Raised when data processing fails."""
    pass


class CoordinateError(TopoConvertError):
    """Raised when coordinate transformation or validation fails."""
    pass


class InterpolationError(ProcessingError):
    """Raised when interpolation fails."""
    pass


class MeshGenerationError(ProcessingError):
    """Raised when mesh generation fails."""
    pass


class ContourGenerationError(ProcessingError):
    """Raised when contour generation fails."""
    pass