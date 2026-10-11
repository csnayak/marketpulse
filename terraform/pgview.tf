resource "docker_image" "pgview" {
  name         = "sosedoff/pgweb:0.16.2"
  keep_locally = true
}

resource "docker_container" "pgview" {
  name    = "marketpulse-pgview"
  image   = docker_image.pgview.image_id
  restart = "unless-stopped"

  # Auto-connects on startup (no connection form) since PGWEB_DATABASE_URL is set.
  env = [
    "PGWEB_DATABASE_URL=postgresql://${var.postgres_user}:${urlencode(var.postgres_password)}@postgres:5432/${var.postgres_db}?sslmode=disable",
  ]

  ports {
    internal = 8081
    external = var.pgview_port
    ip       = "127.0.0.1"
  }

  networks_advanced {
    name = docker_network.marketpulse.name
  }

  depends_on = [docker_container.postgres]
}
