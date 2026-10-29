# GCP Terraform plan policy checker

## Problem

Check a Terraform plan before deployment and fail CI when planned infrastructure breaks a simple policy. This version of coding challenge #8 checks Google Cloud Storage resources.

## Rules

- Every planned Cloud Storage bucket must set `public_access_prevention = "enforced"`.
- Every planned bucket must have nonempty `environment` and `owner` labels.
- Planned bucket IAM member, binding, or policy resources must not grant access to `allUsers` or `allAuthenticatedUsers`.

The checker reads `resource_changes` from `terraform show -json`. It ignores resources being deleted. Unknown required values fail the check because their safety cannot be confirmed before apply. A violation exits with code 1; an invalid input exits with code 2. The script does not call Google Cloud or change resources.

## Quick demo

Python 3.9 or newer is the only requirement for the checker:

```bash
python check_plan.py examples/pass-plan.json
# PASS: GCP storage policy checks passed

python check_plan.py examples/fail-plan.json
# FAIL: google_storage_bucket.example: public access prevention must be enforced
# FAIL: google_storage_bucket.example: missing labels: owner
# FAIL: google_storage_bucket_iam_member.public: public IAM member allUsers is not allowed
```

The failing example exits with code 1, which fails a CI job. Run tests with `python -m unittest discover -s tests -v`.

## Check a real GCP plan

[`examples/main.tf`](examples/main.tf) is a minimal safe bucket configuration. It is for generating a plan; do not run `terraform apply` for this demo. Verify that `gcloud auth list` shows the intended account, sign in for application default credentials if needed, then run:

```bash
terraform -chdir=examples init
terraform -chdir=examples plan -var="project_id=YOUR_PROJECT_ID" \
  -var="bucket_name=GLOBALLY_UNIQUE_BUCKET_NAME" -out=tfplan
terraform -chdir=examples show -json tfplan > plan.json
python check_plan.py plan.json
```

The plan file and JSON output can contain sensitive values. Keep them local; the included `.gitignore` excludes the paths above. GitHub Actions runs the offline tests and sample checks without GCP credentials.
