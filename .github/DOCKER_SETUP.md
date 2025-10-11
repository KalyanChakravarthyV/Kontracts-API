# Docker Hub Setup for GitHub Actions

This document explains how to configure the GitHub Actions workflow to push Docker images to Docker Hub.

## Prerequisites

1. A Docker Hub account
2. Access to the GitHub repository settings

## Setup Instructions

### 1. Create Docker Hub Access Token

1. Log in to [Docker Hub](https://hub.docker.com/)
2. Go to **Account Settings** → **Security** → **Access Tokens**
3. Click **New Access Token**
4. Give it a name (e.g., `github-actions-kontracts-api`)
5. Set permissions to **Read & Write**
6. Click **Generate**
7. **Copy the token** (you won't be able to see it again!)

### 2. Add Secrets to GitHub Repository

1. Go to your GitHub repository: https://github.com/KalyanChakravarthyV/Kontracts-API
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

   **Secret 1: Docker Username**
   - **Name**: `DOCKER_USERNAME`
   - **Value**: Your Docker Hub username (e.g., `kvadlakonda`)

   **Secret 2: Docker Password**
   - **Name**: `DOCKER_PASSWORD`
   - **Value**: Paste the Docker Hub access token you copied earlier

5. Click **Add secret** for each

### 3. Verify the Workflow

The workflow is configured in `.github/workflows/docker-build-push.yml` and will:

- **Trigger on**:
  - Push to `main` or `develop` branches
  - Pull requests to `main`
  - Version tags (e.g., `v1.0.0`)
  - Manual workflow dispatch

- **Build and push images with tags**:
  - `<username>/kontracts-api:latest` (on main branch)
  - `<username>/kontracts-api:main` (on main branch)
  - `<username>/kontracts-api:develop` (on develop branch)
  - `<username>/kontracts-api:v1.0.0` (on version tags)
  - `<username>/kontracts-api:main-<git-sha>` (commit SHA)

- **Multi-platform support**: Builds for both `linux/amd64` and `linux/arm64`

## Docker Image Details

- **Docker Hub Repository**: `<your-username>/kontracts-api` (based on DOCKER_USERNAME secret)
- **Base Image**: Python 3.11-slim
- **Exposed Port**: 8000
- **Health Check**: Configured for `/health` endpoint

## Using the Docker Image

### Pull the image

```bash
docker pull <your-username>/kontracts-api:latest
```

### Run the container

```bash
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:password@host:port/database" \
  -e OPENAI_API_KEY="your-api-key" \
  --name kontracts-api \
  <your-username>/kontracts-api:latest
```

### Using docker-compose

```yaml
version: '3.8'

services:
  api:
    image: <your-username>/kontracts-api:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/kontracts
      - OPENAI_API_KEY=your-api-key
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=kontracts
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Troubleshooting

### Workflow fails with "unauthorized" error
- Verify the `DOCKER_PASSWORD` secret is correctly set in GitHub
- Ensure the Docker Hub access token has Read & Write permissions
- Check that the token hasn't expired

### Image not found on Docker Hub
- Make sure the workflow has completed successfully
- Check the Actions tab in GitHub for any errors
- Verify you're pushing to a branch that triggers the workflow

### Multi-platform build fails
- This is usually due to GitHub Actions runner limitations
- The workflow uses Docker Buildx with cache to optimize builds
- Check the workflow logs for specific platform errors

## Manual Workflow Trigger

You can manually trigger the workflow:

1. Go to **Actions** tab in GitHub
2. Select **Build and Push Docker Image** workflow
3. Click **Run workflow**
4. Select the branch
5. Click **Run workflow**

This is useful for rebuilding images without making code changes.
