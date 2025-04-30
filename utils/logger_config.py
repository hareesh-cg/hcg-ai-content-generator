import logging
import os
import sys # To potentially write initial warnings to stderr

# Flag to ensure setup runs only once per Lambda container lifecycle
_logging_configured = False

DEFAULT_LOG_LEVEL = "INFO"
VALID_LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

def setup_logging():
    """
    Configures the root logger based on the LOG_LEVEL environment variable.
    This should be called ONCE at the start of the Lambda handler.
    """
    global _logging_configured
    if _logging_configured:
        # print("Logging already configured for this execution environment.") # Optional debug print
        return # Avoid reconfiguring in warm starts

    log_level_name = os.environ.get('LOG_LEVEL', DEFAULT_LOG_LEVEL).upper()

    if log_level_name not in VALID_LOG_LEVELS:
        # Use stderr for initial warning as logger might not be fully working yet
        print(f"WARNING: Invalid LOG_LEVEL '{log_level_name}'. Defaulting to {DEFAULT_LOG_LEVEL}.", file=sys.stderr)
        log_level_name = DEFAULT_LOG_LEVEL

    log_level = logging.getLevelName(log_level_name)

    # Get the root logger
    root_logger = logging.getLogger()
    
    root_logger.setLevel(log_level)

    _logging_configured = True
    
    # Use the root logger itself to confirm setup (this will now respect the level)
    logging.info(f"Root logger configured. Log level set to: {log_level_name}")


def get_logger(name: str) -> logging.Logger:
    """Gets a logger instance with the given name."""
    # The logger will inherit level and formatting from the root logger configured by setup_logging()
    return logging.getLogger(name)