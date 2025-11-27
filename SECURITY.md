# Security Configuration

This document outlines the security measures implemented in Crawling Chaos and how to maintain them.

## Security Model

The application follows a defense-in-depth approach with multiple layers of security:

### 1. Network Isolation

**Docker Network Isolation:**
- API and database containers run on an isolated Docker network
- Only necessary ports are exposed to localhost (127.0.0.1)
- No services are directly accessible from external networks

**Port Bindings:**
```yaml
postgres: 127.0.0.1:5432:5432  # Database only on localhost
api:      127.0.0.1:5000:5000  # API only on localhost
```

**Result:**
- Database: Accessible only from host system and Docker containers
- API: Accessible only from host system (for nginx to proxy)
- External networks: Cannot directly access either service

### 2. Nginx Reverse Proxy Restrictions

The nginx configuration implements strict access controls:

**Publicly Accessible:**
- `/` - Frontend dashboard (HTML/CSS/JS)
- `/api/data/*` - Read-only data endpoints (needed for dashboard to display news/analyses)
- Static files (CSS, JS, images)

**Blocked from Public Access:**
- `/api/jobs` - Job management endpoints
- `/api/scheduler/*` - Scheduler control endpoints
- `/api/templates/*` - Template endpoints
- `/api/health` - Health check (localhost only)
- All other `/api/*` endpoints

**Configuration:**
```nginx
# Block administrative endpoints
location ~ ^/api/(jobs|scheduler|templates) {
    deny all;
    return 403 "Access denied";
}

# Allow read-only data endpoints
location ~ ^/api/data/ {
    # Public access with rate limiting
    limit_req zone=api_limit burst=10 nodelay;
    proxy_pass http://crawling_chaos_api;
}

# Block all other API endpoints
location ~ ^/api/ {
    deny all;
    return 403 "Access denied";
}
```

### 3. What Users Can Access

**Public Users (via web browser):**
- ✅ View the dashboard
- ✅ See collected news articles
- ✅ Read Claude and GPT analyses
- ❌ Create or modify jobs
- ❌ Start/stop the scheduler
- ❌ Access administrative functions
- ❌ Query the database directly

**Administrators (via localhost/SSH):**
- ✅ All of the above
- ✅ Create and manage jobs via localhost:5000
- ✅ Control the scheduler
- ✅ Access database on localhost:5432
- ✅ View API health checks

## Administrative Access

To perform administrative tasks, you must have SSH/local access to the server.

### Managing Jobs from Localhost

```bash
# SSH into server
ssh user@your-server.com

# Create a job
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d @/opt/crawling-chaos/api/templates/news_analysis_job.json

# List all jobs
curl http://localhost:5000/api/jobs

# Execute a specific job
curl -X POST http://localhost:5000/api/jobs/1/execute

# Start scheduler
curl -X POST http://localhost:5000/api/scheduler/start

# Check scheduler status
curl http://localhost:5000/api/jobs/status
```

### Database Access from Localhost

```bash
# Connect to database
psql -h localhost -p 5432 -U postgres -d crawling_chaos

# Or using Docker exec
docker exec -it crawling-chaos-db psql -U postgres -d crawling_chaos
```

## Rate Limiting

Rate limiting is enforced by nginx to prevent abuse:

**API Data Endpoints:**
- Limit: 10 requests/second per IP
- Burst: 10 additional requests allowed
- Applies to: `/api/data/*`

**General Pages:**
- Limit: 30 requests/second per IP
- Burst: 20 additional requests allowed
- Applies to: `/` and static files

**Blocked Endpoints:**
- No rate limiting needed (all requests denied)

### Adjusting Rate Limits

Edit your nginx configuration:

```nginx
# In the http block
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=general_limit:10m rate=30r/s;
```

## Whitelisting IPs for Administrative Access

If you need to allow administrative access from specific IPs (e.g., office network):

### Option 1: Add IP Whitelist to Nginx

```nginx
# Create a geo block for whitelisted IPs
geo $admin_access {
    default 0;
    127.0.0.1 1;        # localhost
    192.168.1.0/24 1;   # internal network
    203.0.113.50 1;     # specific external IP
}

# Update administrative endpoints
location ~ ^/api/(jobs|scheduler|templates) {
    if ($admin_access = 0) {
        return 403 "Access denied";
    }

    proxy_pass http://crawling_chaos_api;
    # ... rest of proxy config
}
```

### Option 2: Use VPN or SSH Tunnel

More secure option - access via VPN or SSH tunnel:

```bash
# SSH tunnel from your local machine
ssh -L 5000:localhost:5000 user@your-server.com

# Now access admin API on your local machine
curl http://localhost:5000/api/jobs
```

## SSL/TLS Configuration

The nginx templates include modern TLS configuration:

**Enabled Protocols:**
- TLS 1.2
- TLS 1.3

**Disabled:**
- SSL v2/v3
- TLS 1.0/1.1

**Security Features:**
- Forward secrecy (ECDHE ciphers)
- HSTS (HTTP Strict Transport Security)
- OCSP stapling
- Session resumption for performance

## Security Headers

The following security headers are configured:

```nginx
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self' 'unsafe-inline' 'unsafe-eval'
```

## API Keys and Secrets

**Storage:**
- API keys stored in `.env` file
- `.env` file excluded from git (via `.gitignore`)
- Never commit API keys to version control

**File Permissions:**
```bash
# Restrict .env file to owner only
chmod 600 .env

# Verify permissions
ls -l .env
# Should show: -rw------- (600)
```

**Environment Variables:**
- `ANTHROPIC_API_KEY` - Claude API access
- `OPENAI_API_KEY` - GPT API access
- `DB_PASSWORD` - Database password (even though not publicly accessible)

## Database Security

**Network Access:**
- Bound to localhost only (127.0.0.1:5432)
- Not accessible from external networks
- Accessible from Docker network for API container

**Authentication:**
- Change default credentials in production
- Use strong passwords

**Production Hardening:**
```yaml
# docker-compose.yaml
environment:
  POSTGRES_DB: crawling_chaos
  POSTGRES_USER: ${DB_USER}        # from .env
  POSTGRES_PASSWORD: ${DB_PASSWORD} # from .env
```

```bash
# .env
DB_USER=your_custom_user
DB_PASSWORD=your_strong_password_here
```

## Monitoring and Logging

**Nginx Access Logs:**
```bash
/var/log/nginx/crawling-chaos-access.log
```

**Nginx Error Logs:**
```bash
/var/log/nginx/crawling-chaos-error.log
```

**Check for suspicious activity:**
```bash
# Check for 403 responses (blocked requests)
grep "403" /var/log/nginx/crawling-chaos-access.log

# Check for unusual patterns
tail -f /var/log/nginx/crawling-chaos-access.log
```

**Docker Logs:**
```bash
# API logs
docker logs crawling-chaos-api

# Database logs
docker logs crawling-chaos-db
```

## Security Checklist

Use this checklist for deployment and regular audits:

- [ ] Docker ports bound to 127.0.0.1 only
- [ ] Nginx administrative endpoints blocked
- [ ] HTTPS enabled with valid certificate
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] `.env` file permissions set to 600
- [ ] API keys not committed to git
- [ ] Database using non-default credentials
- [ ] Firewall configured (ports 22, 80, 443 only)
- [ ] Regular updates applied to host system
- [ ] Logs monitored for suspicious activity
- [ ] Automated backups configured
- [ ] SSL certificate auto-renewal working

## Updating Security Configuration

After modifying security settings:

1. **Test nginx configuration:**
```bash
sudo nginx -t
```

2. **Reload nginx (zero-downtime):**
```bash
sudo systemctl reload nginx
```

3. **Restart Docker containers if needed:**
```bash
cd /opt/crawling-chaos
docker-compose down
docker-compose up -d
```

4. **Verify restrictions:**
```bash
# Should succeed (public endpoint)
curl https://news.example.com/api/data/news

# Should fail with 403 (blocked endpoint)
curl https://news.example.com/api/jobs

# Should succeed from localhost
curl http://localhost:5000/api/jobs
```

## Incident Response

If you suspect a security breach:

1. **Check access logs for unusual activity:**
```bash
sudo tail -100 /var/log/nginx/crawling-chaos-access.log
```

2. **Check which IPs accessed blocked endpoints:**
```bash
grep "403" /var/log/nginx/crawling-chaos-access.log | awk '{print $1}' | sort | uniq -c | sort -rn
```

3. **Temporarily block suspicious IPs:**
```bash
# Add to nginx config
deny 203.0.113.100;
```

4. **Rotate API keys if compromised:**
```bash
# Update .env with new keys
nano .env

# Restart API container
docker-compose restart api
```

5. **Check database for unauthorized changes:**
```bash
docker exec -it crawling-chaos-db psql -U postgres -d crawling_chaos

# Check recent job creations
SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10;
```

## Additional Hardening (Optional)

For high-security environments, consider:

1. **Fail2ban for automated IP blocking**
2. **WAF (Web Application Firewall) like ModSecurity**
3. **Database encryption at rest**
4. **VPN requirement for all administrative access**
5. **Two-factor authentication for SSH**
6. **Intrusion detection system (IDS)**
7. **Regular security audits and penetration testing**

---

**Last Updated:** 2025-01-27
**Reviewed By:** System Administrator
