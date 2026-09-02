from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from django.contrib.auth import (
    get_user_model,
)

from inbox.models import (
    Organization,
)

from knowledge.services.backfill_service import (
    KnowledgeBackfillService,
)


User = get_user_model()


class Command(BaseCommand):

    help = (
        "Backfill KnowledgeEvidence and "
        "KnowledgeFacts from governed InboxMessage records."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--organization",
            type=int,
            help="Organization ID",
        )

        parser.add_argument(
            "--user",
            type=int,
            help="User ID",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of messages",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Reprocess existing knowledge",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Resolve coverage without creating "
                "Knowledge rows."
            ),
        )


    def handle(
        self,
        *args,
        **options,
    ):

        organization = None

        user = None


        if options[
            "organization"
        ]:

            organization = (
                Organization.objects.get(
                    id=(
                        options[
                            "organization"
                        ]
                    )
                )
            )


        if options[
            "user"
        ]:

            user = (
                User.objects.get(
                    id=(
                        options[
                            "user"
                        ]
                    )
                )
            )


        service = (
            KnowledgeBackfillService()
        )


        if options[
            "dry_run"
        ]:

            results = (
                service.preview(
                    organization=organization,
                    user=user,
                    limit=(
                        options[
                            "limit"
                        ]
                    ),
                )
            )

            self.stdout.write(
                ""
            )

            self.stdout.write(
                "="
                *
                60
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "ONE UCH KNOWLEDGE BACKFILL DRY RUN"
                )
            )

            self.stdout.write(
                "="
                *
                60
            )

            self.stdout.write(
                f"Total      : {results['total']}"
            )

            self.stdout.write(
                f"Matched    : {results['matched']}"
            )

            self.stdout.write(
                f"Unmatched  : {results['unmatched']}"
            )

            self.stdout.write(
                f"Ambiguous  : {results['ambiguous']}"
            )

            self.stdout.write(
                f"Coverage   : {results['coverage_rate']}%"
            )

            self.stdout.write(
                "="
                *
                60
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "PASS - READ-ONLY KNOWLEDGE COVERAGE COMPLETE"
                )
            )

            return


        self.stdout.write(
            ""
        )

        self.stdout.write(
            "="
            *
            60
        )

        self.stdout.write(
            self.style.SUCCESS(
                "ONE UCH KNOWLEDGE BACKFILL"
            )
        )

        self.stdout.write(
            "="
            *
            60
        )


        results = (
            service.process(
                organization=organization,
                user=user,
                limit=(
                    options[
                        "limit"
                    ]
                ),
                force=(
                    options[
                        "force"
                    ]
                ),
            )
        )


        self.stdout.write(
            ""
        )

        self.stdout.write(
            f"Processed : {results['processed']}"
        )

        self.stdout.write(
            f"Matched   : {results['matched']}"
        )

        self.stdout.write(
            f"Unmatched : {results['unmatched']}"
        )

        self.stdout.write(
            f"Ambiguous : {results['ambiguous']}"
        )

        self.stdout.write(
            f"Skipped   : {results['skipped']}"
        )

        self.stdout.write(
            f"Failed    : {results['failed']}"
        )

        self.stdout.write(
            f"Total     : {results['total']}"
        )

        self.stdout.write(
            f"Coverage  : {results['coverage_rate']}%"
        )

        self.stdout.write(
            f"Elapsed   : {results['elapsed']} sec"
        )

        self.stdout.write(
            f"Success   : {results['success_rate']}%"
        )

        self.stdout.write(
            f"Speed     : {results['throughput']} msg/sec"
        )

        self.stdout.write(
            f"Job       : {results['job_status']}"
        )


        if results[
            "failed"
        ]:

            raise CommandError(
                "Knowledge backfill completed with failures."
            )


        self.stdout.write(
            ""
        )

        self.stdout.write(
            "="
            *
            60
        )

        self.stdout.write(
            self.style.SUCCESS(
                "BACKFILL COMPLETED"
            )
        )

        self.stdout.write(
            "="
            *
            60
        )
