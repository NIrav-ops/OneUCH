from django.test import TestCase

from platform_core.api.mixins import (
    ListMixin,
    RetrieveMixin,
    CreateMixin,
    UpdateMixin,
    DeleteMixin,
)


class EnterpriseMixinTests(TestCase):

    def test_list_mixin_exists(self):

        self.assertTrue(

            issubclass(

                ListMixin,

                object,

            )

        )

    def test_retrieve_mixin_exists(self):

        self.assertTrue(

            issubclass(

                RetrieveMixin,

                object,

            )

        )

    def test_create_mixin_exists(self):

        self.assertTrue(

            issubclass(

                CreateMixin,

                object,

            )

        )

    def test_update_mixin_exists(self):

        self.assertTrue(

            issubclass(

                UpdateMixin,

                object,

            )

        )

    def test_delete_mixin_exists(self):

        self.assertTrue(

            issubclass(

                DeleteMixin,

                object,

            )

        )