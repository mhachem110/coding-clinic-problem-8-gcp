#!/usr/bin/env python3
"""Check a Terraform JSON plan for a small set of GCP storage rules."""

import json
import sys
from pathlib import Path


# These Google IAM members would make a bucket accessible to the public.
PUBLIC = {"allUsers", "allAuthenticatedUsers"}
# Every bucket needs these labels so its purpose and owner are clear.
REQUIRED_LABELS = ("environment", "owner")


def check_plan(plan):
    # Terraform's JSON plan lists proposed changes under "resource_changes".
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        raise ValueError("expected a Terraform plan with resource_changes")

    # Collect every violation so one run can show everything to fix.
    problems = []
    for resource in changes:
        # Only managed resources that will exist after the plan need checking.
        if resource.get("mode") != "managed":
            continue
        change = resource.get("change", {})
        if change.get("actions") == ["delete"]:
            continue
        # "after" describes the resource's planned configuration.
        after = change.get("after") or {}
        address = resource.get("address", "unknown resource")
        kind = resource.get("type")

        if kind == "google_storage_bucket":
            # Block a bucket unless public access prevention is explicitly on.
            if after.get("public_access_prevention") != "enforced":
                problems.append(f"{address}: public access prevention must be enforced")
            # Missing or empty required labels are both violations.
            labels = after.get("labels") or {}
            missing = [key for key in REQUIRED_LABELS if not labels.get(key)]
            if missing:
                problems.append(f"{address}: missing labels: {', '.join(missing)}")

        if kind == "google_storage_bucket_iam_member":
            # A member resource grants one identity access to a bucket.
            member = after.get("member")
            if member in PUBLIC:
                problems.append(f"{address}: public IAM member {member} is not allowed")
            elif member is None:
                # If Terraform cannot tell us the member yet, do not assume it is safe.
                problems.append(f"{address}: IAM member cannot be checked before apply")

        if kind == "google_storage_bucket_iam_binding":
            # A binding can grant the same role to several members.
            members = after.get("members")
            if members is None:
                problems.append(f"{address}: IAM members cannot be checked before apply")
            elif any(member in PUBLIC for member in members):
                problems.append(f"{address}: public IAM members are not allowed")

        if kind == "google_storage_bucket_iam_policy":
            # A full IAM policy stores its bindings as a JSON string.
            policy_data = after.get("policy_data")
            if not isinstance(policy_data, str):
                problems.append(f"{address}: IAM policy cannot be checked before apply")
            else:
                policy = json.loads(policy_data)
                members = [member for binding in policy.get("bindings", [])
                           for member in binding.get("members", [])]
                if any(member in PUBLIC for member in members):
                    problems.append(f"{address}: public IAM policy is not allowed")

    # An empty list means the plan passed all of these rules.
    return problems


def main():
    # The command expects exactly one path to a Terraform plan JSON file.
    if len(sys.argv) != 2:
        print("Usage: python check_plan.py PLAN.json", file=sys.stderr)
        return 2
    try:
        # Read the file, turn JSON into Python data, and check the policy.
        plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        problems = check_plan(plan)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        # Exit 2 means the command or input was invalid, not a policy violation.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if problems:
        # Exit 1 means the plan broke at least one policy rule.
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    # Exit 0 means no violations were found.
    print("PASS: GCP storage policy checks passed")
    return 0


if __name__ == "__main__":
    # Pass main's exit code (0, 1, or 2) back to the terminal and CI.
    sys.exit(main())
