NAME=cardnews
TAG=latest
DOCKER_USER=achil7

IMG=${NAME}:${TAG}

# Build Docker image
build:
	docker build -f deploy/Dockerfile -t ${IMG} .

# Tag image for Docker Hub
tag:
	docker tag ${IMG} ${DOCKER_USER}/${IMG}

# Push to Docker Hub
push:
	docker push ${DOCKER_USER}/${IMG}

# All in one deployment (build + tag + push)
deploy: build tag push

# Clean up old images
clean:
	docker image prune -a -f

# Help
help:
	@echo "=== Docker Deployment ==="
	@echo "  make build    - Build Docker image"
	@echo "  make tag      - Tag image for Docker Hub"
	@echo "  make push     - Push image to Docker Hub"
	@echo "  make deploy   - Build, tag, and push (all in one)"
	@echo ""
	@echo "=== Local ==="
	@echo "  python main.py           - Run once"
	@echo "  python main.py --daemon  - Run as scheduler daemon"
	@echo ""
	@echo "=== Server ==="
	@echo "  cd deploy && ./deploy.sh - Pull and start on server"
	@echo ""
	@echo "=== Cleanup ==="
	@echo "  make clean    - Clean up old images"
