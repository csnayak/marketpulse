resource "docker_image" "backend" {
  name         = "marketpulse-backend:local"
  keep_locally = true

  build {
    context    = "${path.module}/.."
    dockerfile = "backend/Dockerfile"
    tag        = ["marketpulse-backend:local"]
  }

  triggers = {
    source_hash = sha256(join("", concat(
      [
        filesha256("${path.module}/../requirements.txt"),
        filesha256("${path.module}/../backend/Dockerfile"),
      ],
      [for file in local.backend_files : filesha256("${path.module}/../backend/src/${file}")]
    )))
  }
}

resource "docker_container" "api" {
  name    = "marketpulse-api"
  image   = docker_image.backend.image_id
  command = ["uvicorn", "marketpulse.api_main:app", "--host", "0.0.0.0", "--port", "8000"]
  restart = "unless-stopped"

  env = [
    "DATABASE_URL=${local.postgres_url}",
    "PRICE_STALE_AFTER_SECONDS=${var.price_stale_after_seconds}",
  ]

  ports {
    internal = 8000
    external = 8000
    ip       = "127.0.0.1"
  }

  healthcheck {
    test         = ["CMD", "python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=3)"]
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
