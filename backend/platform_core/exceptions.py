class PlatformError(Exception):
    """
    Base platform exception.
    """
    pass


class ServiceNotRegistered(
    PlatformError,
):
    """
    Raised when service
    does not exist.
    """
    pass