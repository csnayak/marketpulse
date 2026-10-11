resource "docker_container" "coinbase_worker" {
  name    = "marketpulse-coinbase-worker"
  image   = docker_image.api_service.image_id
  command = ["pixi", "run", "worker"]
  restart = "unless-stopped"

  env = [
    "DATABASE_URL=${local.postgres_url}",
    "STATS_REFRESH_INTERVAL_SECONDS=${var.price_refresh_interval_seconds}",
    "CATALOG_REFRESH_INTERVAL_SECONDS=${var.catalog_refresh_interval_seconds}",
    "COINBASE_REQUEST_TIMEOUT_SECONDS=${var.coinbase_request_timeout_seconds}",
    "LOG_LEVEL=${var.log_level}",
  ]

  networks_advanced {
    name = docker_network.marketpulse.name
  }

  depends_on = [docker_container.postgres]
}
