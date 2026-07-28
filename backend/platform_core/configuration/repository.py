class ConfigurationRepository:

    _settings = {}

    @classmethod
    def set(

        cls,

        key,

        value,

    ):

        cls._settings[key] = value

    @classmethod
    def get(

        cls,

        key,

        default=None,

    ):

        return cls._settings.get(

            key,

            default,

        )

    @classmethod
    def all(

        cls,

    ):

        return dict(

            cls._settings,

        )

    @classmethod
    def clear(

        cls,

    ):

        cls._settings.clear()