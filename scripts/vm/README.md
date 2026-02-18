# VM Ops Scripts

These scripts are the canonical VM operation utilities used on `openclaw-vm`.

- `install_openclaw.sh`: bootstrap/update OpenClaw source and Python environment.
- `validate_response.py`: end-to-end runtime validator (Vertex upstream + local service checks).

On VM, wrapper scripts in `/home/mm/` call these repo versions to avoid drift.
