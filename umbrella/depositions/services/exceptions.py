class SubmissionValidationError(Exception):
    """An expected validation failure with a message safe to show to the user."""

    def __init__(self, public_message):
        self.public_message = public_message
        super().__init__(public_message)
