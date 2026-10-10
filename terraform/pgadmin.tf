resource "docker_image" "pgadmin" {
  name         = "dpage/pgadmin4:9.18"
  keep_locally = true
}

resource "docker_container" "pgadmin" {
  name    = "marketpulse-pgadmin"
  image   = docker_image.pgadmin.image_id
  restart = "unless-stopped"

  env = [
    "PGADMIN_DEFAULT_EMAIL=${var.pgadmin_email}",
    "PGADMIN_DEFAULT_PASSWORD=${var.pgadmin_password}",
    "PGADMIN_DISABLE_POSTFIX=1",
  ]

  ports {
    internal = 80
    external = var.pgadmin_port
    ip       = "127.0.0.1"
  }

  mounts {
    target = "/var/lib/pgadmin"
    source = docker_volume.pgadmin_data.name
    type   = "volume"
  }

  networks_advanced {
    name = docker_network.marketpulse.name
  }

  depends_on = [docker_container.postgres]
}
