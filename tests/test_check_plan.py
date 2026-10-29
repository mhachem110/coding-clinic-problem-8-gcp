import copy
import json
import unittest
from pathlib import Path

from check_plan import check_plan


# Find the example plans from the repository root, wherever tests are run.
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class PlanPolicyTests(unittest.TestCase):
    """Check both the sample plans and edge cases for each policy rule."""

    def test_safe_gcp_plan_passes(self):
        # The safe sample should produce no violations.
        plan = json.loads((EXAMPLES / "pass-plan.json").read_text())
        self.assertEqual(check_plan(plan), [])

    def test_unsafe_gcp_plan_reports_each_problem(self):
        # The unsafe sample has three separate issues, including public IAM.
        plan = json.loads((EXAMPLES / "fail-plan.json").read_text())
        problems = check_plan(plan)
        self.assertEqual(len(problems), 3)
        self.assertTrue(any("allUsers" in problem for problem in problems))

    def test_deleted_bucket_is_ignored(self):
        # A resource being removed cannot expose a bucket after deployment.
        plan = json.loads((EXAMPLES / "fail-plan.json").read_text())
        plan["resource_changes"] = [copy.deepcopy(plan["resource_changes"][0])]
        plan["resource_changes"][0]["change"]["actions"] = ["delete"]
        self.assertEqual(check_plan(plan), [])

    def test_unknown_public_setting_fails_closed(self):
        # An unset protection setting should not be treated as safe.
        plan = json.loads((EXAMPLES / "pass-plan.json").read_text())
        del plan["resource_changes"][0]["change"]["after"]["public_access_prevention"]
        self.assertIn("public access prevention", check_plan(plan)[0])

    def test_uncheckable_iam_member_fails_closed(self):
        # Reject an IAM grant if its member is unknown until deployment.
        plan = json.loads((EXAMPLES / "fail-plan.json").read_text())
        plan["resource_changes"] = [plan["resource_changes"][1]]
        plan["resource_changes"][0]["change"]["after"] = {}
        self.assertIn("cannot be checked", check_plan(plan)[0])

    def test_public_iam_binding_is_rejected(self):
        # IAM bindings can list public members too.
        plan = {"resource_changes": [{
            "address": "google_storage_bucket_iam_binding.public",
            "mode": "managed",
            "type": "google_storage_bucket_iam_binding",
            "change": {"actions": ["create"],
                       "after": {"members": ["allAuthenticatedUsers"]}},
        }]}
        self.assertIn("public IAM", check_plan(plan)[0])

    def test_public_iam_policy_is_rejected(self):
        # A full IAM policy can hide public members inside policy_data JSON.
        plan = {"resource_changes": [{
            "address": "google_storage_bucket_iam_policy.public",
            "mode": "managed",
            "type": "google_storage_bucket_iam_policy",
            "change": {"actions": ["create"], "after": {
                "policy_data": json.dumps({"bindings": [{"members": ["allUsers"]}]})}},
        }]}
        self.assertIn("public IAM", check_plan(plan)[0])

    def test_invalid_plan_is_rejected(self):
        # Without resource_changes, the input is not a usable plan.
        with self.assertRaises(ValueError):
            check_plan({})


if __name__ == "__main__":
    unittest.main()
