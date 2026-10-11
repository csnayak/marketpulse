output "api_url" {
  description = "Local API documentation URL."
  value       = "http://localhost:8010/docs"
}

output "frontend_url" {
  description = "Local MarketPulse frontend URL."
  value       = "http://localhost:${var.frontend_port}"
}

output "pgadmin_url" {
  description = "Local pgAdmin URL."
  value       = "http://localhost:${var.pgadmin_port}"
}

output "dozzle_url" {
  description = "Local container logs dashboard URL."
  value       = "http://localhost:${var.dozzle_port}"
}

output "pgview_url" {
  description = "Local pgweb (pgview) database browser URL."
  value       = "http://localhost:${var.pgview_port}"
}

output "postgres_container" {
  value = docker_container.postgres.name
}
