from django.contrib.auth.base_user import BaseUserManager


class UserManager(
    BaseUserManager
):

    def create_user(
        self,
        email,
        password=None,
        **extra_fields,
    ):
        """
        Create and save a One UCH user.

        Work-email identity is normalized to
        lowercase because authentication is
        case-insensitive.
        """

        if not email:
            raise ValueError(
                "Email is required"
            )

        email = (
            self.normalize_email(
                str(email).strip()
            )
            .lower()
        )

        user = self.model(
            email=email,
            **extra_fields,
        )

        user.set_password(
            password
        )

        user.save(
            using=self._db
        )

        return user

    def create_superuser(
        self,
        email,
        password,
        **extra_fields,
    ):

        extra_fields.setdefault(
            "is_staff",
            True,
        )

        extra_fields.setdefault(
            "is_superuser",
            True,
        )

        extra_fields.setdefault(
            "role",
            "admin",
        )

        return self.create_user(
            email=email,
            password=password,
            **extra_fields,
        )
