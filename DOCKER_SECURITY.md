# Docker Security Guide

## 🔒 Security Overview

This document explains security measures for running ClawdBot in Docker.

---

## ⚠️ Security Risks

### Potential Risks

1. **API Key Exposure**
   - Risk: Keys in environment variables or logs
   - Mitigation: Use `.env` file (not committed), secrets management

2. **Network Exposure**
   - Risk: Services exposed to internet
   - Mitigation: Bind to localhost only (127.0.0.1)

3. **Container Breakout**
   - Risk: Privilege escalation
   - Mitigation: Non-root user, read-only filesystem, dropped capabilities

4. **Resource Exhaustion**
   - Risk: Container consuming too many resources
   - Mitigation: CPU/memory limits in docker-compose.yml

5. **Data Leakage**
   - Risk: Sensitive data in volumes
   - Mitigation: Minimal volumes, no secrets in volumes

---

## ✅ Security Measures Implemented

### 1. Non-Root User
```dockerfile
USER clawdbot  # Runs as UID 1000, not root
```

### 2. Read-Only Filesystem
```yaml
read_only: true  # Prevents modifications
```

### 3. Dropped Capabilities
```yaml
cap_drop:
  - ALL  # No special privileges
```

### 4. Localhost Binding
```yaml
ports:
  - "127.0.0.1:18789:18789"  # Only accessible from host
```

### 5. Resource Limits
```yaml
limits:
  cpus: '2.0'
  memory: 2G
```

### 6. No API Keys in Image
- Keys via environment variables only
- `.env` file in `.gitignore`
- Example file provided (`.env.example`)

---

## 🚀 Safe Usage

### Step 1: Create .env File

```bash
cp .env.example .env
# Edit .env with YOUR keys (NEVER commit this file!)
nano .env
```

### Step 2: Verify .gitignore

```bash
# Ensure .env is ignored
grep "^\.env$" .gitignore
```

### Step 3: Build Image

```bash
# Build without exposing secrets
docker-compose build
```

### Step 4: Run in Isolated Mode

```bash
# Test without network (safe)
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs
```

### Step 5: Test Locally Only

```bash
# Access only via localhost
curl http://localhost:8080/health

# Gateway on localhost
wscat -c ws://localhost:18789
```

---

## 🔍 Security Checklist

Before running:

- [ ] API keys in `.env` (not in Dockerfile or docker-compose.yml)
- [ ] `.env` in `.gitignore`
- [ ] Ports bound to 127.0.0.1 (not 0.0.0.0)
- [ ] Non-root user configured
- [ ] Read-only filesystem enabled
- [ ] Capabilities dropped
- [ ] Resource limits set
- [ ] No sensitive data in volumes
- [ ] Network isolation configured
- [ ] Health check enabled

---

## ⚡ Quick Test (Safe Mode)

```bash
# 1. Create minimal .env (without real keys)
cat > .env << 'EOF'
ANTHROPIC_API_KEY=demo-key-for-testing
OPENAI_API_KEY=demo-key-for-testing
CLAWDBOT_ENV=demo
EOF

# 2. Build image
docker-compose build

# 3. Run status check (doesn't need API keys)
docker-compose run --rm clawdbot python -m clawdbot.cli status

# 4. Cleanup
docker-compose down
rm .env
```

---

## 🛡️ Production Recommendations

### DO NOT use this setup for production without:

1. **Secrets Management**
   - Use Docker secrets or external vault
   - AWS Secrets Manager / HashiCorp Vault
   - Kubernetes secrets

2. **Network Security**
   - Use internal networks only
   - VPN or private network
   - Firewall rules

3. **Access Control**
   - Authentication for all endpoints
   - Rate limiting
   - IP whitelisting

4. **Monitoring**
   - Security monitoring
   - Intrusion detection
   - Log aggregation

5. **Updates**
   - Regular security updates
   - Dependency scanning
   - Vulnerability monitoring

---

## 🔐 Additional Security

### Enable Complete Network Isolation

```yaml
networks:
  clawdbot-net:
    internal: true  # No internet access
```

### Use Secrets (Docker Swarm/Kubernetes)

```yaml
secrets:
  anthropic_key:
    external: true
```

### Scan for Vulnerabilities

```bash
# Scan image
docker scan clawdbot-test

# Check dependencies
pip-audit
```

---

## 📞 Security Issues

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. Email security contact (if available)
3. Provide details privately
4. Allow time for patch

---

## 🎯 Testing Without Risk

### Safe Demo Mode

```bash
# Run without any API keys
docker-compose run --rm \
  -e ANTHROPIC_API_KEY="" \
  -e OPENAI_API_KEY="" \
  clawdbot python -m clawdbot.cli status

# Shows features without making API calls
```

### Verify Security

```bash
# Check user
docker-compose run --rm clawdbot whoami
# Should show: clawdbot (not root)

# Check capabilities
docker-compose run --rm clawdbot capsh --print
# Should show no capabilities

# Check ports
netstat -tlnp | grep 18789
# Should show 127.0.0.1:18789 (not 0.0.0.0:18789)
```

---

## ✅ Summary

**This configuration is reasonably secure for:**
- ✅ Local testing
- ✅ Development
- ✅ Learning

**DO NOT use as-is for:**
- ❌ Production deployment
- ❌ Internet-facing services
- ❌ Multi-tenant environments

**Always:**
- Keep API keys secret
- Update dependencies regularly
- Monitor for security issues
- Follow security best practices

---

**Last Updated**: 2026-01-28  
**Version**: 0.3.0  
**Security Level**: Development/Testing Only
