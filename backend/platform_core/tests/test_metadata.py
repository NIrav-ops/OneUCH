from django.test import TestCase

from platform_core.api.metadata import (
    ResponseMetadata,
)


class MetadataTests(TestCase):

    def test_metadata_contains_version(self):

        meta = ResponseMetadata.build()

        self.assertIn(

            "api_version",

            meta,

        )

    def test_metadata_contains_request(self):

        meta = ResponseMetadata.build()

        self.assertIn(

            "request_id",

            meta,

        )

    def test_metadata_contains_timestamp(self):

        meta = ResponseMetadata.build()

        self.assertIn(

            "timestamp",

            meta,

        )

    def test_metadata_contains_pagination(self):

        meta = ResponseMetadata.build()

        self.assertIn(

            "pagination",

            meta,

        )