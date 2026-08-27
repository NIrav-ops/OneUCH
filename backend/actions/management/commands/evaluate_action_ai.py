from django.conf import settings
from django.core.management.base import (
    BaseCommand,
)

from actions.ai_evaluation_cases import (
    ACTION_AI_EVALUATION_CASES,
    REFERENCE_TIME,
)

from actions.services.ai_extractor import (
    extract_actions_with_ai_result,
)

from actions.services.extraction_policy import (
    decide_ai_action,
)


class Command(BaseCommand):
    help = (
        "Evaluate One UCH AI Action extraction "
        "against the controlled semantic corpus."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--case",
            dest="case_id",
            type=str,
            default=None,
        )

    def handle(
        self,
        *args,
        **options,
    ):
        cases = list(
            ACTION_AI_EVALUATION_CASES
        )

        case_id = options.get(
            "case_id"
        )

        if case_id:
            cases = [
                case
                for case in cases
                if (
                    case["id"].lower()
                    == case_id.lower()
                )
            ]

            if not cases:
                self.stderr.write(
                    self.style.ERROR(
                        f"Unknown case: {case_id}"
                    )
                )
                return

        limit = options.get(
            "limit"
        )

        if limit is not None:
            cases = cases[
                :max(
                    limit,
                    0,
                )
            ]

        total = 0
        correct_actionability = 0
        due_date_checks = 0
        correct_due_dates = 0
        provider_failures = 0

        auto_create = 0
        review = 0
        ignored = 0

        self.stdout.write(
            ""
        )

        self.stdout.write(
            "One UCH AI Action Evaluation"
        )

        self.stdout.write(
            "=" * 60
        )

        for case in cases:
            total += 1

            result = (
                extract_actions_with_ai_result(
                    subject=case[
                        "subject"
                    ],
                    body=case[
                        "body"
                    ],
                    sender=(
                        "customer@example.com"
                    ),
                    recipient=(
                        "user@oneuch.test"
                    ),
                    provider=(
                        settings
                        .ONEUCH_AI_PROVIDER
                    ),
                    model=(
                        settings
                        .ONEUCH_AI_MODEL
                    ),
                    message_id=None,
                    reference_time=(
                        REFERENCE_TIME
                    ),
                )
            )

            if not result.success:
                provider_failures += 1

                self.stdout.write(
                    self.style.ERROR(
                        (
                            f"{case['id']} "
                            f"PROVIDER_FAILURE | "
                            f"{result.error}"
                        )
                    )
                )

                continue

            candidates = (
                result.candidates
            )

            actual_action = bool(
                candidates
            )

            expected_action = bool(
                case[
                    "expected_action"
                ]
            )

            actionability_ok = (
                actual_action
                == expected_action
            )

            if actionability_ok:
                correct_actionability += 1

            status = (
                "PASS"
                if actionability_ok
                else "FAIL"
            )

            output = (
                f"{case['id']} "
                f"{status} | "
                f"expected_action="
                f"{expected_action} | "
                f"actual_action="
                f"{actual_action}"
            )

            if candidates:
                top = candidates[0]

                confidence = top.get(
                    "confidence_score",
                    0,
                )

                decision = (
                    decide_ai_action(
                        confidence_score=(
                            confidence
                        ),
                        auto_create_threshold=(
                            settings
                            .ACTION_AI_AUTO_CREATE_THRESHOLD
                        ),
                        review_threshold=(
                            settings
                            .ACTION_AI_REVIEW_THRESHOLD
                        ),
                    )
                )

                if (
                    decision.decision
                    == "auto_create"
                ):
                    auto_create += 1

                elif (
                    decision.decision
                    == "review"
                ):
                    review += 1

                else:
                    ignored += 1

                output += (
                    f" | confidence="
                    f"{confidence}"
                    f" | policy="
                    f"{decision.decision}"
                    f" | title="
                    f"{top.get('title')!r}"
                )

                expected_due = (
                    case.get(
                        "expected_due_date"
                    )
                )

                if expected_due:
                    due_date_checks += 1

                    actual_due = (
                        top[
                            "due_date"
                        ].date().isoformat()
                        if top.get(
                            "due_date"
                        )
                        else None
                    )

                    due_ok = (
                        actual_due
                        == expected_due
                    )

                    if due_ok:
                        correct_due_dates += 1

                    output += (
                        f" | expected_due="
                        f"{expected_due}"
                        f" | actual_due="
                        f"{actual_due}"
                        f" | due="
                        f"{'PASS' if due_ok else 'FAIL'}"
                    )

            if actionability_ok:
                self.stdout.write(
                    self.style.SUCCESS(
                        output
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        output
                    )
                )

        self.stdout.write(
            ""
        )

        self.stdout.write(
            "=" * 60
        )

        self.stdout.write(
            "SUMMARY"
        )

        actionability_pct = (
            (
                correct_actionability
                / total
                * 100
            )
            if total
            else 0
        )

        self.stdout.write(
            (
                "Actionability: "
                f"{correct_actionability}/"
                f"{total} "
                f"({actionability_pct:.1f}%)"
            )
        )

        if due_date_checks:
            due_pct = (
                correct_due_dates
                / due_date_checks
                * 100
            )

            self.stdout.write(
                (
                    "Due dates: "
                    f"{correct_due_dates}/"
                    f"{due_date_checks} "
                    f"({due_pct:.1f}%)"
                )
            )

        self.stdout.write(
            (
                "Policy distribution: "
                f"auto_create={auto_create}, "
                f"review={review}, "
                f"ignore={ignored}"
            )
        )

        self.stdout.write(
            (
                "Provider failures: "
                f"{provider_failures}"
            )
        )

        self.stdout.write(
            ""
        )

        self.stdout.write(
            "No database writes were performed."
        )
