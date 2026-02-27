# Integration Tests

Integration tests require a real (or sandbox) Landscape instance.

## Setup

Set these environment variables before running:

```bash
export LSCTL_URL="https://your-landscape-instance.example.com"
export LSCTL_ACCESS_KEY="your-access-key"
export LANDSCAPE_SECRET_KEY="your-secret-key"
export LSCTL_ACCOUNT="standalone"
```

## Run

```bash
pytest tests/integration/ -v
```

Integration tests are skipped automatically if `LSCTL_URL` is not set.
