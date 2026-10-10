locals {
  frontend_files = sort(tolist(fileset("${path.module}/../frontend/src", "**")))
}

resource "docker_image" "frontend" {
  name         = "marketpulse-frontend:local"
  keep_locally = true

  build {
    context = "${path.module}/../frontend"
    tag     = ["marketpulse-frontend:local"]
  }

  triggers = {
    source_hash = sha256(join("", concat(
      [
        filesha256("${path.module}/../frontend/Dockerfile"),
        filesha256("${path.module}/../frontend/.dockerignore"),
        filesha256("${path.module}/../frontend/nginx.conf"),
        filesha256("${path.module}/../frontend/package.json"),
        filesha256("${path.module}/../frontend/package-lock.json"),
        filesha256("${path.module}/../frontend/index.html"),
        filesha256("${path.module}/../frontend/vite.config.ts"),
      ],
      [for file in local.frontend_files : filesha256("${path.module}/../frontend/src/${file}")]
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
