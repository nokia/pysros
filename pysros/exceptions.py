# Copyright 2021 Nokia

__all__ = ("SrosMgmtError", "InvalidPathError", "ModelProcessingError", "InternalError", "SrosConfigConflictError", "ActionTerminatedIncompleteError", )

class SrosMgmtError(Exception):
    """Exception raised by the :mod:`pysros.management` objects when:

    * data is missing
    * incorrect combinations of datastore and operation are performed
    * validation fails when using :py:meth:`pysros.management.Datastore.set`
    * invalid objects are passed to the operation e.g. :py:meth:`pysros.management.Datastore.set`

    .. Reviewed by PLM 20210625
    .. Reviewed by TechComms 20210630
    """
    pass

class InvalidPathError(Exception):
    """Exception raised when a path provided by the user:

    * is empty
    * fails to parse
    * does not point to an existing object
    * is missing list keys that must be provided

    .. Reviewed by PLM 20210625
    .. Reviewed by TechComms 20210630
    """
    pass

class ModelProcessingError(Exception):
    """Exception raised when an error occurs during processing of the YANG model (schema) when:

    * a YANG file cannot be found
    * a YANG file is malformed

    .. Reviewed by PLM 20210625
    .. Reviewed by TechComms 20210630
    """
    pass

class InternalError(Exception):
    """Exception raised for broader issues when:

    * schema creation fails and this unfinished schema is utilized

    .. Reviewed by PLM 20210625
    .. Reviewed by TechComms 20210630
    """
    pass

class SrosConfigConflictError(Exception):
    """Exception raised when a configuration commit failed due to conflicts between the ``candidate``
    datastore and the ``baseline`` datastore.  Retrying the configuration operation usually resolves the
    situation.  If retrying does not resolve the issue, the connection should be closed using
    :py:meth:`pysros.management.Connection.disconnect` and the operation restarted to make a new connection.

    .. Reviewed by PLM 20210625
    .. Reviewed by TechComms 20210630
    """
    pass

class ActionTerminatedIncompleteError(Exception):
    """Exception raised when an action completes with a ``terminated-incomplete`` status"""
    pass

def make_exception(arg, **kwarg):
    return arg[0](arg[1].format(**kwarg))
