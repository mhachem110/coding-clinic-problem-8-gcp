#!/usr/bin/env python3
"""Check a Terraform JSON plan for a small set of GCP storage rules."""

import json
import sys
from pathlib import Path


PUBLIC = {"allUsers", "allAuthenticatedUsers"}
REQUIRED_LABELS = ("environment", "owner")


def check_plan(plan):
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        raise ValueError("expected a Terraform plan with resource_changes")

    problems = []
    for resource in changes:
        if resource.get("mode") != "managed":
            continue
        change = resource.get("change", {})
        if change.get("actions") == ["delete"]:
            continue
        after = change.get("after") or {}
        address = resource.get("address", "unknown resource")
        kind = resource.get("type")

        if kind == "google_storage_bucket":
            if after.get("public_access_prevention") != "enforced":
                problems.append(f"{address}: public access prevention must be enforced")
            labels = after.get("labels") or {}
            missing = [key for key in REQUIRED_LABELS if not labels.get(key)]
            if missing:
                problems.append(f"{address}: missing labels: {', '.join(missing)}")

        if kind == "google_storage_bucket_iam_member":
            member = after.get("member")
            if member in PUBLIC:
                problems.append(f"{address}: public IAM member {member} is not allowed")
            elif member is None:
                problems.append(f"{address}: IAM member cannot be checked before apply")

        if kind == "google_storage_bucket_iam_binding":
            members = after.get("members")
            if members is None:
                problems.append(f"{address}: IAM members cannot be checked before apply")
            elif any(member in PUBLIC for member in members):
                problems.append(f"{address}: public IAM members are not allowed")

        if kind == "google_storage_bucket_iam_policy":
            policy_data = after.get("policy_data")
            if not isinstance(policy_data, str):
                problems.append(f"{address}: IAM policy cannot be checked before apply")
            else:
                policy = json.loads(policy_data)
                members = [member for binding in policy.get("bindings", [])
                           for member in binding.get("members", [])]
                if any(member in PUBLIC for member in members):
                    problems.append(f"{address}: public IAM policy is not allowed")

    return problems


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_plan.py PLAN.json", file=sys.stderr)
        return 2
    try:
        plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        problems = check_plan(plan)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    print("PASS: GCP storage policy checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
