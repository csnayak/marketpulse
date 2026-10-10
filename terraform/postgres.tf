resource "docker_image" "postgres" {
  name         = "postgres:17-alpine"
  keep_locally = true
}

resource "docker_container" "postgres" {
  name    = "marketpulse-postgres"
  image   = docker_image.postgres.image_id
  restart = "unless-stopped"

  env = [
    "POSTGRES_DB=${var.postgres_db}",
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
  ]

  ports {
    internal = 5432
    external = var.postgres_port
    ip       = "127.0.0.1"
  }

  mounts {
    target = "/var/lib/postgresql/data"
    source = docker_volume.postgres_data.name
    type   = "volume"
  }

  mounts {
    target    = "/docker-entrypoint-initdb.d/001_marketpulse_schema.sql"
    source    = abspath("${path.module}/db-schema/schema.sql")
    type      = "bind"
    read_only = true
  }

  healthcheck {
    test         = ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
    interval     = "5s"
    timeout      = "3s"
    retries      = 12
    start_period = "5s"
  }

  networks_advanced {
    name    = docker_network.marketpulse.name
    aliases = ["postgres"]
  }

  wait = true
}
