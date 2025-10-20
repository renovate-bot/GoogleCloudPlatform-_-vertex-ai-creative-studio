import logging

# Dedicated logger for tracking the suppressed error
race_condition_logger = logging.getLogger("genmedia.race_condition_tracker")

class GenerationError(Exception):
    """Custom exception for video generation errors."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class UnknownHandlerIdFilter(logging.Filter):
    """A logging filter to suppress 'Unknown handler id' errors."""
    def filter(self, record):
        # Suppress the specific benign error message from Mesop
        if "Unknown handler id" in record.getMessage():
            # Log to a separate, non-disruptive logger for tracking purposes
            race_condition_logger.info("Suppressed 'Unknown handler id' error", extra={"original_record": record.getMessage()})
            return False # Prevent the original logger from processing it
        return True
