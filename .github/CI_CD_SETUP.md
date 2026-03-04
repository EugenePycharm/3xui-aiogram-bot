# CI/CD Setup for GitHub Actions

## Secrets Configuration

Go to **GitHub Repository → Settings → Secrets and variables → Actions** and add these secrets:

### Required Secrets

| Secret | Description | Example |
|--------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token (main bot) | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `ADMIN_BOT_TOKEN` | Telegram admin bot token | `987654321:ZYXwvutsrqponMLKJIHGFEDCBA` |
| `DATABASE_URL` | Database connection URL | `sqlite+aiosqlite:///data/bot.db` or `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `SSH_HOST` | SSH server hostname/IP | `192.168.1.100` or `example.com` |
| `SSH_USER` | SSH username | `deploy` or `root` |
| `SSH_PORT` | SSH port | `22` |
| `SSH_PRIVATE_KEY` | SSH private key for deployment | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DEPLOY_PATH` | Path on server for deployment | `/home/deploy/vpn-bot` |

### Optional Secrets (for 3x-ui server config)

| Secret | Description | Default |
|--------|-------------|---------|
| `SERVER_API_URL` | 3x-ui panel API URL | - |
| `SERVER_USERNAME` | 3x-ui panel username | - |
| `SERVER_PASSWORD` | 3x-ui panel password | - |
| `SERVER_LOCATION` | Server location name | `Default` |
| `SERVER_NAME` | Server display name | `Server-1` |
| `SERVER_MAX_CLIENTS` | Max clients per server | `50` |
| `ADMIN_TELEGRAM_IDS` | Admin Telegram IDs (comma-separated) | - |
| `DB_USER` | PostgreSQL database user | `vpnbot` |
| `DB_PASSWORD` | PostgreSQL database password | - |
| `DB_NAME` | PostgreSQL database name | `vpnbot` |
| `LOG_LEVEL` | Application log level | `INFO` |

## SSH Key Setup

Generate SSH key for deployment:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f github_deploy_key
```

Add public key to server `~/.ssh/authorized_keys`:

```bash
cat github_deploy_key.pub | ssh SSH_USER@SSH_HOST "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Add private key to GitHub Secrets as `SSH_PRIVATE_KEY`:

```bash
cat github_deploy_key | gh secret set SSH_PRIVATE_KEY
```

## Workflow Triggers

### CI Workflow (`ci.yml`)
- Runs on every push to `main`/`master`
- Runs on every pull request
- Checks: linting, type checking, Docker validation, security scan

### CD Workflow (`cd.yml`)
- Runs on push to `main`/`master`
- Runs on version tags (`v1.0.0`)
- Manual trigger via GitHub Actions UI
- Actions: build Docker images, push to GHCR, deploy via SSH

## Manual Deployment

Go to **Actions → CD → Run workflow** to trigger manual deployment.

## Environment Variables in Workflow

The CD workflow automatically creates `.env` file on the server from secrets. No need to manage it manually.

## Troubleshooting

### Build fails
- Check `pyproject.toml` and `uv.lock` are in sync
- Run `uv sync` locally to verify dependencies

### Deploy fails
- Verify SSH key has correct permissions on server
- Check `DEPLOY_PATH` exists and is writable
- Ensure Docker and Docker Compose are installed on server
- Verify `SSH_HOST`, `SSH_USER`, `SSH_PORT` are correct

### Container fails to start
- Check logs: `docker compose -f docker-compose.prod.yml logs`
- Verify all secrets are set correctly
- Check database connection string format
