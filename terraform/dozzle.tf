resource "docker_image" "dozzle" {
  name         = "amir20/dozzle:v11.3.0"
  keep_locally = true
}

resource "docker_container" "dozzle" {
  name    = "marketpulse-dozzle"
  image   = docker_image.dozzle.image_id
  restart = "unless-stopped"

  ports {
    internal = 8080
    external = var.dozzle_port
    ip       = "127.0.0.1"
  }

  mounts {
    target    = "/var/run/docker.sock"
    source    = "/var/run/docker.sock"
    type      = "bind"
    read_only = true
  }

  mounts {
    target = "/data"
    source = docker_volume.dozzle_data.name
    type   = "volume"
  }

  healthcheck {
    test         = ["CMD", "/dozzle", "healthcheck"]
    interval     = "30s"
    timeout      = "5s"
    retries      = 3
    start_period = "10s"
  }

  wait = true

  depends_on = [
    docker_container.api,
    docker_container.coinbase_worker,
    docker_container.pgadmin,
  ]
}
