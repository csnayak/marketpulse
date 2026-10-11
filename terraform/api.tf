resource "docker_image" "api_service" {
  name         = "marketpulse-api-service:local"
  keep_locally = true

  build {
    context    = "${path.module}/.."
    dockerfile = "api-service/Dockerfile"
    tag        = ["marketpulse-api-service:local"]
  }

  triggers = {
    source_hash = sha256(join("", concat(
      [
        filesha256("${path.module}/../pixi.toml"),
        filesha256("${path.module}/../pixi.lock"),
        filesha256("${path.module}/../api-service/Dockerfile"),
      ],
      [for file in local.api_service_files : filesha256("${path.module}/../api-service/src/${file}")]
    )))
  }
}

resource "docker_container" "api" {
  name    = "marketpulse-dashboard-api"
  image   = docker_image.api_service.image_id
  restart = "unless-stopped"

  env = [
    "DATABASE_URL=${local.postgres_url}",
    "PRICE_STALE_AFTER_SECONDS=${var.price_stale_after_seconds}",
  ]

  ports {
    internal = 8010
    external = 8010
    ip       = "127.0.0.1"
  }

  healthcheck {
    test         = ["CMD", "pixi", "run", "python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8010/api/v1/health/ready', timeout=3)"]
    interval     = "30s"
    timeout      = "5s"
    retries      = 3
    start_period = "10s"
  }

  wait         = true
  wait_timeout = 90

  networks_advanced {
    name = docker_network.marketpulse.name
  }

  depends_on = [docker_container.postgres]
}
