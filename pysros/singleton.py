# Copyright 2021-2024 Nokia

class _Singleton(type):
    _instances = {}

    def __new__(cls, *args, **kwargs):
        res = super(_Singleton, cls).__new__(cls, *args, **kwargs)
        res.__copy__ = lambda self: self
        res.__deepcopy__ = lambda self, memo: self
        res.__reduce__ = lambda self: (self.__class__, ())
        return res

    def __call__(cls, *args, **kwargs):
        assert args == () and kwargs == {}
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class _Empty(metaclass=_Singleton):
    """Representation of whether empty leaf is present.

    .. Reviewed by TechComms 20210712
    """

    def __str__(self):
        return "Empty"

    def __repr__(self):
        return "Empty"


Empty = _Empty()
Empty.__doc__ = """Define the YANG ``empty`` type.

    The YANG ``empty`` type is not the same as an empty string ``""`` or as the ``None``
    type in Python.  It requires specific translation depending on whether it is being
    used in XML or in JSON IETF encodings.

    The :py:class:`Empty` class is used to represent the value of a node that is of the
    YANG type ``empty``.

    .. code-block:: python
       :caption: Example - Obtaining YANG ``empty`` type values
       :name: pysros-singleton-empty-example-get

       >>> connection_object.running.get('/nokia-conf:configure/system/grpc/allow-unsecure-connection')
       Leaf(Empty)

    .. code-block:: python
       :caption: Example - Configuring a YANG ``empty`` type
       :name: pysros-singleton-empty-example-set

       >>> from pysros.management import Empty
       >>> connection_object.candidate.set('/nokia-conf:configure/system/grpc/allow-unsecure-connection', Empty)

    .. Reviewed by PLM 20230228
    .. Reviewed by TechComms 20230302

"""
