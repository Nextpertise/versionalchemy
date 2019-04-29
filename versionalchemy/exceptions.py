class LogTableCreationError(Exception):
    """
    Thrown if an invariant is violated when registering a table for versioning with versionalchemy.
    """
    pass


class RestoreError(Exception):
    pass


class LogIdentifyError(Exception):
    pass


class HistoryItemNotFound(Exception):
    pass
