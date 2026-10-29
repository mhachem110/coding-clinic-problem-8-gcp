terraform {
  # Download the Google provider so Terraform understands GCP resources.
  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }
}

variable "project_id" {
  # Supply the GCP project when creating a plan.
  type = string
}

variable "bucket_name" {
  # Bucket names must be globally unique across Google Cloud.
  type = string
}

provider "google" {
  project = var.project_id
}

resource "google_storage_bucket" "example" {
  # This is a safe example for the policy checker; the demo does not apply it.
  name                        = var.bucket_name
  location                    = "US-CENTRAL1"
  uniform_bucket_level_access = true
  # The checker requires public access prevention to be enforced.
  public_access_prevention = "enforced"

  # The checker also requires both labels to have values.
  labels = {
    environment = "demo"
    owner       = "training"
  }
}
