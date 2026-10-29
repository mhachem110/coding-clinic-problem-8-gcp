terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }
}

variable "project_id" {
  type = string
}

variable "bucket_name" {
  type = string
}

provider "google" {
  project = var.project_id
}

resource "google_storage_bucket" "example" {
  name                        = var.bucket_name
  location                    = "US-CENTRAL1"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  labels = {
    environment = "demo"
    owner       = "training"
  }
}
