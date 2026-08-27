from django.conf import settings
from django.core.management.base import (
    BaseCommand,
)

from approvals.ai_evaluation_cases import (
    APPROVAL_AI_EVALUATION_CASES,
    REFERENCE_TIME,
)

from approvals.services.ai_extractor import (
    extract_approvals_with_ai_result,
)


class Command(BaseCommand):
    help = (
        "Evaluate One UCH AI Approval extraction "
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
            APPROVAL_AI_EVALUATION_CASES
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
        correct_approval_detection = 0

        due_date_checks = 0
        correct_due_dates = 0

        provider_failures = 0

        confidence_values = []

        true_positives = 0
        true_negatives = 0
        false_positives = 0
        false_negatives = 0

        self.stdout.write(
            ""
        )

        self.stdout.write(
            "One UCH AI Approval Evaluation"
        )

        self.stdout.write(
            "=" * 68
        )

        for case in cases:
            total += 1

            result = (
                extract_approvals_with_ai_result(
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

            actual_approval = bool(
                candidates
            )

            expected_approval = bool(
                case[
                    "expected_approval"
                ]
            )

            detection_ok = (
                actual_approval
                == expected_approval
            )

            if detection_ok:
                correct_approval_detection += 1

            if (
                expected_approval
                and actual_approval
            ):
                true_positives += 1

            elif (
                not expected_approval
                and not actual_approval
            ):
                true_negatives += 1

            elif (
                not expected_approval
                and actual_approval
            ):
                false_positives += 1

            else:
                false_negatives += 1

            status = (
                "PASS"
                if detection_ok
                else "FAIL"
            )

            output = (
                f"{case['id']} "
                f"{status} | "
                f"expected_approval="
                f"{expected_approval} | "
                f"actual_approval="
                f"{actual_approval}"
            )

            if candidates:
                top = candidates[0]

                confidence = int(
                    top.get(
                        "confidence_score",
                        0,
                    )
                )

                confidence_values.append(
                    confidence
                )

                output += (
                    f" | confidence="
                    f"{confidence}"
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

            if detection_ok:
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
            "=" * 68
        )

        self.stdout.write(
            "SUMMARY"
        )

        detection_pct = (
            (
                correct_approval_detection
                / total
                * 100
            )
            if total
            else 0
        )

        self.stdout.write(
            (
                "Approval detection: "
                f"{correct_approval_detection}/"
                f"{total} "
                f"({detection_pct:.1f}%)"
            )
        )

        self.stdout.write(
            (
                "Confusion matrix: "
                f"TP={true_positives}, "
                f"TN={true_negatives}, "
                f"FP={false_positives}, "
                f"FN={false_negatives}"
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

        if confidence_values:
            self.stdout.write(
                (
                    "Confidence range: "
                    f"min={min(confidence_values)}, "
                    f"max={max(confidence_values)}, "
                    f"avg="
                    f"{sum(confidence_values) / len(confidence_values):.1f}"
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
