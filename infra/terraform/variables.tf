variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "bucket_name" {
  type = string
}

variable "api_image" {
  type = string
}

variable "worker_image" {
  type = string
}

variable "sql_tier" {
  type    = string
  default = "db-g1-small"
}

variable "database_password" {
  type      = string
  sensitive = true
}
