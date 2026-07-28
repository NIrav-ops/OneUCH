from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):

    def create_user(
        self,
        email,
        password=None,
        **extra_fields,
    ):
        """
        Create and save a regular user.
        """

        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields,
        )

        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        email,
        password,
        **extra_fields,
    ):
        """
        Create and save a superuser.
        """

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