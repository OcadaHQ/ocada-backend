class SnipsError(Exception):
    """Base class for exceptions in this module."""
    pass

class SnipsInsuficientFundsError(SnipsError):
    """Exception raised when there is not enough funds to execute a transaction."""
    pass

class SnipsInsufficientInstrumentQuantityError(SnipsError):
    """Exception raised when there is not enough shares to execute a transaction."""
    pass

class SnipsInvalidExternalTokenError(SnipsError):
    """Exception raised when the token is invalid."""
    pass

class SnipsWeeklyXPResetError(SnipsError):
    """Exception raise when users' weekly XP fails to reset."""
    pass