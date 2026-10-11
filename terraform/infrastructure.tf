locals {
  postgres_url      = "postgresql+psycopg://${var.postgres_user}:${urlencode(var.postgres_password)}@postgres:5432/${var.postgres_db}"
  api_service_files = sort(tolist(fileset("${path.module}/../api-service/src", "**")))
}

resource "docker_network" "marketpulse" {
  name = "marketpulse"
}

resource "docker_volume" "postgres_data" {
  name = "marketpulse_postgres_data"
}

resource "docker_volume" "pgadmin_data" {
  name = "marketpulse_pgadmin_data"
}

resource "docker_volume" "dozzle_data" {
  name = "marketpulse_dozzle_data"
}
