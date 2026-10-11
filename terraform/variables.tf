variable "postgres_db" {
  description = "PostgreSQL database name."
  type        = string
  default     = "marketpulse"
}

variable "postgres_user" {
  description = "PostgreSQL application user."
  type        = string
  default     = "marketpulse"
}

variable "postgres_password" {
  description = "Local PostgreSQL password. Terraform stores this value in its state."
  type        = string
  sensitive   = true
  default     = "marketpulse_local"
}

variable "postgres_port" {
  description = "Host port for PostgreSQL, bound to localhost."
  type        = number
  default     = 5432
}

variable "pgadmin_email" {
  description = "Local pgAdmin login email."
  type        = string
  default     = "admin@marketpulse.dev"
}

variable "pgadmin_password" {
  description = "Local pgAdmin password. Terraform stores this value in its state."
  type        = string
  sensitive   = true
  default     = "pgadmin_local"
}

variable "pgadmin_port" {
  description = "Host port for pgAdmin, bound to localhost."
  type        = number
  default     = 5050
}

variable "dozzle_port" {
  description = "Host port for Dozzle, bound to localhost."
  type        = number
  default     = 8080
}

variable "pgview_port" {
  description = "Host port for pgweb (pgview), bound to localhost."
  type        = number
  default     = 8081
}

variable "frontend_port" {
  description = "Host port for the MarketPulse frontend, bound to localhost."
  type        = number
  default     = 5173
}

variable "price_refresh_interval_seconds" {
  type    = number
  default = 60
}

variable "catalog_refresh_interval_seconds" {
  type    = number
  default = 3600
}

variable "price_stale_after_seconds" {
  type    = number
  default = 180
}

variable "coinbase_request_timeout_seconds" {
  type    = number
  default = 8
}

variable "log_level" {
  type    = string
  default = "INFO"
}
