import copy
import json
import unittest
from pathlib import Path

from check_plan import check_plan


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class PlanPolicyTests(unittest.TestCase):
    def test_safe_gcp_plan_passes(self):
        plan = json.loads((EXAMPLES / "pass-plan.json").read_text())
        self.assertEqual(check_plan(plan), [])

    def test_unsafe_gcp_plan_reports_each_problem(self):
        plan = json.loads((EXAMPLES / "fail-plan.json").read_text())
        problems = check_plan(plan)
        self.assertEqual(len(problems), 3)
        self.assertTrue(any("allUsers" in problem for problem in problems))

    def test_deleted_bucket_is_ignored(self):
        plan = json.loads((EXAMPLES / "fail-plan.json").read_text())
        plan["resource_changes"] = [copy.deepcopy(plan["resource_changes"][0])]
        plan["resource_changes"][0]["change"]["actions"] = ["delete"]
        self.assertEqual(check_plan(plan), [])

    def test_unknown_public_setting_fails_closed(self):
        plan = json.loads((EXAMPLES / "pass-plan.json").read_text())
        del plan["resource_changes"][0]["change"]["after"]["public_access_prevention"]
        self.assertIn("public access prevention", check_plan(plan)[0])

    def test_uncheckable_iam_member_fails_closed(self):
        plan = json.loads((EXAMPLES / "fail-plan.json").read_text())
        plan["resource_changes"] = [plan["resource_changes"][1]]
        plan["resource_changes"][0]["change"]["after"] = {}
        self.assertIn("cannot be checked", check_plan(plan)[0])

    def test_public_iam_binding_is_rejected(self):
        plan = {"resource_changes": [{
            "address": "google_storage_bucket_iam_binding.public",
            "mode": "managed",
            "type": "google_storage_bucket_iam_binding",
            "change": {"actions": ["create"],
                       "after": {"members": ["allAuthenticatedUsers"]}},
        }]}
        self.assertIn("public IAM", check_plan(plan)[0])

    def test_public_iam_policy_is_rejected(self):
        plan = {"resource_changes": [{
            "address": "google_storage_bucket_iam_policy.public",
            "mode": "managed",
            "type": "google_storage_bucket_iam_policy",
            "change": {"actions": ["create"], "after": {
                "policy_data": json.dumps({"bindings": [{"members": ["allUsers"]}]})}},
        }]}
        self.assertIn("public IAM", check_plan(plan)[0])

    def test_invalid_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            check_plan({})


if __name__ == "__main__":
    unittest.main()
