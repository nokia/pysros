# Copyright 2021-2023 Nokia

class _Singleton(type):
    _instances = {}
    def __new__(cls, *args, **kwargs):
        res = super(_Singleton, cls).__new__(cls, *args, **kwargs)
        res.__copy__     = lambda self: self
        res.__deepcopy__ = lambda self, memo: self
        res.__reduce__   = lambda self: (self.__class__, ())
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
Empty.__doc__="""Define the YANG Empty type."""