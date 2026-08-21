terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.40"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_service_account" "api" {
  account_id   = "filing-rag-api"
  display_name = "Filing RAG API"
}

resource "google_service_account" "worker" {
  account_id   = "filing-rag-worker"
  display_name = "Filing RAG Worker"
}

resource "google_storage_bucket" "filings" {
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_sql_database_instance" "postgres" {
  name             = "filing-rag-postgres"
  database_version = "POSTGRES_16"
  region           = var.region
  settings {
    tier              = var.sql_tier
    availability_type = "ZONAL"
    ip_configuration {
      ipv4_enabled = false
    }
  }
  deletion_protection = true
}

resource "google_sql_database" "db" {
  name     = "rag"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app" {
  name     = "rag_app"
  instance = google_sql_database_instance.postgres.name
  password = var.database_password
}

resource "google_cloud_tasks_queue" "processing" {
  name     = "filing-processing"
  location = var.region
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "filing-rag-database-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "filing-rag-openai-api-key"
  replication {
    auto {}
  }
}

resource "google_cloud_run_v2_service" "api" {
  name     = "filing-rag-api"
  location = var.region
  template {
    service_account = google_service_account.api.email
    containers {
      image = var.api_image
      env {
        name  = "APP_ENV"
        value = "production"
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.filings.name
      }
    }
  }
}

resource "google_cloud_run_v2_service" "worker" {
  name     = "filing-rag-worker"
  location = var.region
  template {
    service_account = google_service_account.worker.email
    containers {
      image = var.worker_image
      env {
        name  = "APP_ENV"
        value = "production"
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.filings.name
      }
    }
  }
}

resource "google_storage_bucket_iam_member" "api_writer" {
  bucket = google_storage_bucket.filings.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.api.email}"
}

resource "google_storage_bucket_iam_member" "worker_reader" {
  bucket = google_storage_bucket.filings.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "api_tasks" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.api.email}"
}
