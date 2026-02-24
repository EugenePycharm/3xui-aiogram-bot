# PythonProject — VPN Telegram Bot

## Project Overview

This is a **Telegram bot for VPN subscription management** built with `aiogram 3.x` and `SQLAlchemy`. The bot provides:

- **User registration** with referral system support
- **Trial subscriptions** (7 days, 15GB limit)
- **Paid subscription plans** with VLESS protocol support
- **Payment processing** integration
- **Profile management** for users
- **Support chat** functionality
- **Admin bot** for managing subscriptions, servers, and users

The bot integrates with **3x-ui panels** (Xray/VLESS management) to provision and manage VPN clients on remote servers.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | aiogram 3.x |
| Database | SQLite + SQLAlchemy (async) |
| HTTP Client | aiohttp |
| Environment | python-dotenv |
| Package Manager | uv |
| Python | 3.14+ |

## Project Structure

```
PythonProject/
├── run.py                    # Main bot entry point
├── admin_run.py              # Admin bot entry point
├── add_admin.py              # Script to add admin users
├── pyproject.toml            # Project dependencies (uv)
├── uv.lock                   # Dependency lock file
├── migrate_db.py             # Database migration script
├── clear_db.py               # DB cleanup + 3x-ui client removal
├── fix_trial_plan.py         # Script to fix trial plan settings
├── sync_trials.py            # Script to sync trial subs with 3x-ui
├── app/
│   ├── __init__.py
│   ├── database/
│   │   ├── models.py         # SQLAlchemy models (User, Subscription, Server, Plan, Payment, Admin)
│   │   └── requests.py       # Database query helpers
│   ├── handlers/
│   │   ├── __init__.py       # Router aggregation (main bot)
│   │   ├── start.py          # /start command + referral handling
│   │   ├── profile.py        # User profile commands
│   │   ├── subscription.py   # Subscription management
│   │   ├── payment.py        # Payment processing
│   │   └── support.py        # Support chat handlers
│   ├── handlers/admin/       # Admin bot handlers
│   │   ├── __init__.py       # Admin router aggregation
│   │   ├── subscriptions.py  # Create/manage subscriptions
│   │   ├── users.py          # User management
│   │   └── servers.py        # Server management
│   ├── services/
│   │   ├── subscription.py   # Subscription business logic
│   │   └── referral.py       # Referral system logic
│   ├── api/
│   │   └── three_x_ui.py     # 3x-ui panel API client
│   ├── keyboards/
│   │   ├── reply.py          # Reply keyboards (main menu)
│   │   ├── inline.py         # Inline keyboards (plans, profile, etc.)
│   │   └── admin.py          # Admin bot keyboards
│   ├── middlewares/
│   │   ├── clean_messages.py # Middleware for message cleanup
│   │   └── admin_auth.py     # Admin authentication middleware
│   └── utils/
│       ├── vpn.py            # VPN link generation
│       ├── messages.py       # Message utilities
│       └── admin_utils.py    # Admin utilities (date/traffic parsing)
```

## Database Schema

### Tables

| Table | Description |
|-------|-------------|
| `users` | Telegram users (tg_id, username, balance, referrer) |
| `servers` | 3x-ui server configurations (api_url, credentials, location) |
| `plans` | Subscription plans (price, duration, data_limit) |
| `subscriptions` | Active subscriptions (uuid, email, key_url, expires_at) |
| `payments` | Payment records (amount, status, provider_id) |
| `admins` | Admin users (tg_id, username, is_active) |

## Building and Running

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- Telegram Bot Token (via [@BotFather](https://t.me/BotFather))
- `.env` file with `BOT_TOKEN` and `ADMIN_BOT_TOKEN`

### Installation

```bash
# Install dependencies
uv sync

# Run database migrations (if needed)
python migrate_db.py
```

### Running the Bots

```bash
# Run main user bot
python run.py

# Run admin bot (in separate terminal)
python admin_run.py
```

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `python clear_db.py` | Clear DB and remove all clients from 3x-ui panels |
| `python fix_trial_plan.py` | Fix/create trial plan (7 days, 15GB) |
| `python sync_trials.py` | Sync trial subscriptions with 3x-ui |
| `python migrate_db.py` | Add `received_bonus` column to users table |
| `python add_admin.py <tg_id>` | Add admin user by Telegram ID |
| `python add_admin.py list` | List all admins |

## Environment Variables

Create a `.env` file in the project root:

```env
# Main bot token (for users)
BOT_TOKEN=your_telegram_bot_token_here

# Admin bot token (for admin panel)
ADMIN_BOT_TOKEN=your_admin_bot_token_here
```

## Admin Bot Features

### Creating Subscriptions

The admin bot allows creating subscriptions with custom parameters:

1. **Select user** by Telegram ID
2. **Choose server** from active servers
3. **Set traffic limit** (in GB, or 0 for unlimited)
4. **Select expiration date** using interactive calendar
5. **Automatic provisioning** in 3x-ui panel

### User Management

- View all users with balance and status
- Edit user balance (set, add, or subtract)
- View user subscriptions
- Delete users (with cleanup from 3x-ui)

### Server Management

- Add new 3x-ui servers
- Edit server credentials
- Toggle server active/inactive
- Test connection to server
- View inbounds list
- Delete servers

### Interactive Calendar

The calendar widget supports:
- Month navigation (previous/next)
- Day selection
- Time input (HH:MM format)
- Visual indicators (today, selected)

## Key Features

### Referral System
- Users get a unique referral link (`/start?referrer_id`)
- Referrers receive bonuses when referrals activate trial

### Subscription Management
- **Trial**: 7 days, 15GB (auto-activated for new users)
- **Paid plans**: Configurable via database
- **Custom**: Admin can create with any parameters
- VLESS links generated with `xtls-rprx-vision` flow

### 3x-ui Integration
- Automatic client provisioning on selected servers
- Client update/delete/extend via API
- Multi-server support (load balancing ready)

## Development Conventions

- **Async-first**: All I/O operations use `asyncio`
- **Type hints**: Used throughout the codebase
- **Logging**: Standard `logging` module with structured format
- **Error handling**: Try/except with logging, graceful degradation

## API Reference

### ThreeXUIClient (`app/api/three_x_ui.py`)

| Method | Description |
|--------|-------------|
| `login()` | Authenticate with 3x-ui panel |
| `get_inbounds()` | Fetch available inbounds |
| `add_client()` | Add new VLESS client |
| `update_client()` | Update client (extend, change limits) |
| `delete_client()` | Remove client from panel |

### SubscriptionService (`app/services/subscription.py`)

| Method | Description |
|--------|-------------|
| `issue_subscription()` | Issue new or update existing subscription |
| `activate_trial()` | Activate trial subscription |
| `extend_user_subscription()` | Extend subscription by days |
| `get_subscription_keyboard()` | Generate inline keyboard with links |

## Setup Instructions

### 1. Create Bots

1. Create main bot via [@BotFather](https://t.me/BotFather)
2. Create admin bot via [@BotFather](https://t.me/BotFather)
3. Save both tokens

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your tokens
```

### 3. Add Admin

Find your Telegram ID (use [@userinfobot](https://t.me/userinfobot)):

```bash
python add_admin.py <your_telegram_id>
```

### 4. Start Bots

```bash
# Terminal 1: Main bot
python run.py

# Terminal 2: Admin bot
python admin_run.py
```

### 5. Access Admin Panel

Send `/start` or `/admin` to the admin bot to access the control panel.
