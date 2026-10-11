locals {
  frontend_files = sort(tolist(fileset("${path.module}/../frontend-dashboard/src", "**")))
}

resource "docker_image" "frontend" {
  name         = "marketpulse-frontend-dashboard:local"
  keep_locally = true

  build {
    context = "${path.module}/../frontend-dashboard"
    tag     = ["marketpulse-frontend-dashboard:local"]
  }

  triggers = {
    source_hash = sha256(join("", concat(
      [
        filesha256("${path.module}/../frontend-dashboard/Dockerfile"),
        filesha256("${path.module}/../frontend-dashboard/.dockerignore"),
        filesha256("${path.module}/../frontend-dashboard/nginx.conf"),
        filesha256("${path.module}/../frontend-dashboard/package.json"),
        filesha256("${path.module}/../frontend-dashboard/package-lock.json"),
        filesha256("${path.module}/../frontend-dashboard/index.html"),
        filesha256("${path.module}/../frontend-dashboard/vite.config.ts"),
      ],
      [for file in local.frontend_files : filesha256("${path.module}/../frontend-dashboard/src/${file}")]
    )))
  }
}

resource "docker_container" "frontend" {
  name    = "marketpulse-frontend"
  image   = docker_image.frontend.image_id
  restart = "unless-stopped"

  ports {
    internal = 80
    external = var.frontend_port
    ip       = "127.0.0.1"
  }

  healthcheck {
    test         = ["CMD-SHELL", "wget -q --spider http://127.0.0.1/ || exit 1"]
    interval     = "30s"
    timeout      = "5s"
    retries      = 3
    start_period = "10s"
  }

  wait = true

  networks_advanced {
    name = docker_network.marketpulse.name
  }

  depends_on = [docker_container.api]
}
