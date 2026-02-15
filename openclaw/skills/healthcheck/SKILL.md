---
name: healthcheck
description: "System security and hardening checks"
user-invocable: true
metadata:
  openclaw:
    emoji: "🔒"
    os: ["darwin", "linux"]
---

# System Healthcheck and Security Skill

Perform security checks and system hardening verification.

## Security Checks

### File Permissions

```bash
# Check sensitive file permissions
ls -la ~/.ssh/id_*
ls -la ~/.aws/credentials
ls -la ~/.openclaw/config.json

# Should be 600 or 400 for private files
```

### SSH Configuration

```bash
# Check SSH config
cat ~/.ssh/config

# Verify no weak ciphers
grep -i "Ciphers" /etc/ssh/sshd_config
```

### Firewall Status

**macOS:**
```bash
# Check firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# List applications
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps
```

**Linux:**
```bash
# Check ufw status
sudo ufw status

# Check iptables
sudo iptables -L
```

### Open Ports

```bash
# macOS/Linux
sudo lsof -i -P -n | grep LISTEN

# Or using netstat
netstat -an | grep LISTEN
```

### User Accounts

```bash
# List users
cat /etc/passwd

# Check for users with UID 0 (root privileges)
awk -F: '$3 == 0 {print $1}' /etc/passwd
```

### Updates and Patches

**macOS:**
```bash
softwareupdate -l
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
apt list --upgradable
```

## System Hardening

### Disable Unnecessary Services

```bash
# List running services (macOS)
sudo launchctl list

# List running services (Linux systemd)
systemctl list-units --type=service --state=running
```

### Password Policy

```bash
# Check password policy (Linux)
cat /etc/login.defs | grep PASS_

# Check PAM configuration
cat /etc/pam.d/common-password
```

### Kernel Security

```bash
# Check kernel parameters
sysctl -a | grep -i "kernel\|net"

# Important settings:
# - kernel.randomize_va_space (should be 2)
# - net.ipv4.conf.all.accept_redirects (should be 0)
# - net.ipv4.tcp_syncookies (should be 1)
```

## Audit Checklist

- [ ] SSH keys have proper permissions (600/400)
- [ ] Firewall is enabled
- [ ] No unnecessary ports open
- [ ] System updates are current
- [ ] Strong password policy enforced
- [ ] Disk encryption enabled
- [ ] Automatic updates configured
- [ ] Unnecessary services disabled
- [ ] File system permissions correct
- [ ] Audit logging enabled

## Automated Checks

```bash
#!/bin/bash
# Quick security check script

echo "=== SSH Key Permissions ==="
ls -l ~/.ssh/id_* 2>/dev/null

echo "=== Firewall Status ==="
sudo ufw status 2>/dev/null || sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

echo "=== Open Ports ==="
sudo lsof -i -P -n | grep LISTEN

echo "=== Root Users ==="
awk -F: '$3 == 0 {print $1}' /etc/passwd

echo "=== Updates Available ==="
softwareupdate -l 2>/dev/null || apt list --upgradable 2>/dev/null
```

## Tips

- Run checks regularly
- Document baseline configuration
- Review logs frequently
- Keep systems updated
- Use strong authentication
- Enable audit logging
- Implement least privilege
- Encrypt sensitive data
