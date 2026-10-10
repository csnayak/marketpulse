resource "docker_container" "coinbase_worker" {
  name    = "marketpulse-coinbase-worker"
  image   = docker_image.backend.image_id
  restart = "unless-stopped"

  env = [
    "DATABASE_URL=${local.postgres_url}",
    "PRICE_REFRESH_INTERVAL_SECONDS=${var.price_refresh_interval_seconds}",
    "COINBASE_REQUEST_TIMEOUT_SECONDS=${var.coinbase_request_timeout_seconds}",
    "LOG_LEVEL=${var.log_level}",
  ]

  networks_advanced {
    name = docker_network.marketpulse.name
  }

  depends_on = [docker_container.postgres]
}
