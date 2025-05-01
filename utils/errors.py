class ServiceError(Exception):
    """Base exception class for service layer errors."""
    def __init__(self, message, status_code=500, service_name="UnknownService", details=None):
        """
        Initializes the ServiceError.
        """
        self.message = message
        self.status_code = status_code
        self.service_name = service_name
        self.details = details
        # Create a comprehensive error string
        full_message = f"[{self.service_name} Error][Status {self.status_code}]: {self.message}"
        if self.details:
            full_message += f" | Details: {str(self.details)}"
        super().__init__(full_message)

# You could potentially define more specific common errors here if needed
# class ConfigurationError(ServiceError):
#     def __init__(self, message, service_name="Configuration", details=None):
#         super().__init__(message, status_code=500, service_name=service_name, details=details)

# class NotFoundError(ServiceError):
#     def __init__(self, message, service_name="Resource", details=None):
#         super().__init__(message, status_code=404, service_name=service_name, details=details)

# class ForbiddenError(ServiceError):
#      def __init__(self, message, service_name="Authorization", details=None):
#          super().__init__(message, status_code=403, service_name=service_name, details=details)