"""
Thread-local Request Context Store.
"""

from threading import local


_storage = local()


class RequestStore:

    @staticmethod
    def set(context):

        _storage.context = context

    @staticmethod
    def get():

        return getattr(

            _storage,

            "context",

            None,

        )

    @staticmethod
    def clear():

        if hasattr(

            _storage,

            "context",

        ):

            del _storage.context