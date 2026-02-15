class RFPAutomationError(Exception):
    """Base exception for RFP Automation."""

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class DocumentParsingError(RFPAutomationError):
    """Raised when document parsing fails."""
    pass


class DocumentClassificationError(RFPAutomationError):
    """Raised when document classification fails."""
    pass


class ExtractionError(RFPAutomationError):
    """Raised when AI extraction fails."""
    pass


class ResponseGenerationError(RFPAutomationError):
    """Raised when response generation fails."""
    pass


class ExportError(RFPAutomationError):
    """Raised when document export fails."""
    pass


class StorageError(RFPAutomationError):
    """Raised when file storage operations fail."""
    pass


class AIClientError(RFPAutomationError):
    """Raised when AI API calls fail."""
    pass


class AuthenticationError(RFPAutomationError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(RFPAutomationError):
    """Raised when user lacks permissions."""
    pass
