# OpenClaw VM Operations Runbook

This runbook describes day-to-day operations for the production VM deployment.

## 1. Host and Service

- VM: `openclaw-vm` (zone `us-central1-a`)
- App directory: `/home/mm/openclaw-python`
- Runtime wrapper: `/home/mm/run_openclaw.sh`
- API service: `openclaw.service`

Useful commands:

```bash
sudo systemctl status openclaw --no-pager -l
sudo systemctl restart openclaw
sudo journalctl -u openclaw -n 200 --no-pager
```

## 2. Runtime Authentication

- OpenClaw API auth key is stored at: `/home/mm/.openclaw/api_key`
- The service exports this key as `CLAWDBOT_API__API_KEY`
- API endpoints require either:
  - `x-api-key: <key>`
  - `Authorization: Bearer <key>`

Quick auth check:

```bash
KEY=$(cat /home/mm/.openclaw/api_key)
curl -s -H "x-api-key: $KEY" http://127.0.0.1:8000/agent/sessions
```

## 3. Health Validation

Validation script:

- `/home/mm/validate_response.py`

It verifies:

- Vertex upstream chat completion (GLM-5)
- OpenClaw liveness (`/health/live`)
- API auth (`/agent/sessions`)
- Basic chat and tool-chat (`/agent/chat`)

Run:

```bash
python3 /home/mm/validate_response.py
```

Expected result: `Validation passed: all checks succeeded`.

## 4. Backups

Backup script:

- `/home/mm/backup_openclaw.sh`

Data source:

- `/home/mm/.openclaw`

Backup target:

- `/home/mm/backups/openclaw_backup_YYYYMMDD_HHMMSS.tar.gz`

Retention:

- Default 14 days (`RETENTION_DAYS`, configurable)

Manual backup:

```bash
/home/mm/backup_openclaw.sh
```

## 5. Backup Scheduling

`systemd` timer is used (not cron):

- `openclaw-backup.service`
- `openclaw-backup.timer`

Schedule:

- Daily at `03:30` VM local time (`Asia/Bangkok`)

Check timer:

```bash
sudo systemctl status openclaw-backup.timer --no-pager -l
sudo systemctl list-timers --all | grep openclaw-backup
```

Run backup immediately:

```bash
sudo systemctl start openclaw-backup.service
```

## 6. Restore Procedure

1. Stop service:

```bash
sudo systemctl stop openclaw
```

2. Backup current state (safety):

```bash
/home/mm/backup_openclaw.sh
```

3. Restore from selected archive:

```bash
cd /home/mm
mv .openclaw .openclaw.pre_restore.$(date +%Y%m%d_%H%M%S)
tar -xzf /home/mm/backups/openclaw_backup_YYYYMMDD_HHMMSS.tar.gz -C /home/mm
```

4. Validate permissions and key file:

```bash
chmod 700 /home/mm/.openclaw || true
chmod 600 /home/mm/.openclaw/api_key || true
```

5. Start service:

```bash
sudo systemctl start openclaw
```

6. Run validation:

```bash
python3 /home/mm/validate_response.py
```

## 7. Environment Conventions

- Active Python environment: `/home/mm/openclaw-python/.venv`
- Legacy `/home/mm/openclaw-python/venv` is removed
- Install/update scripts should use `.venv`

## 8. Incident Checklist

If Telegram or API is unresponsive:

1. `sudo systemctl status openclaw --no-pager -l`
2. `sudo journalctl -u openclaw -n 300 --no-pager`
3. `python3 /home/mm/validate_response.py`
4. Verify API key file exists and is non-empty:
   - `/home/mm/.openclaw/api_key`
5. If needed, restart service:
   - `sudo systemctl restart openclaw`
