# Nginx Deployment Guide for Crawling Chaos

This guide covers deploying Crawling Chaos behind Nginx reverse proxy on a multi-domain server.

The application runs in Docker on `localhost:5000`, and Nginx on the host system proxies requests to it. This guide provides nginx configuration templates to help you set up your host nginx.

## Prerequisites
- Nginx installed on host system
- Domain name configured (DNS A record pointing to your server)
- Optional: SSL certificate (Let's Encrypt recommended)

## Step 1: Deploy Application with Docker

```bash
cd /opt/crawling-chaos  # or your preferred location
docker-compose up -d
```

This runs the application on `localhost:5000` (not publicly accessible).

## Step 2: Configure Nginx

Choose the appropriate configuration template based on your needs:

**For HTTPS (Production):**
```bash
sudo cp nginx/crawling-chaos.conf.template /etc/nginx/sites-available/crawling-chaos.conf
sudo nano /etc/nginx/sites-available/crawling-chaos.conf
```

**For HTTP only (Development/Internal):**
```bash
sudo cp nginx/crawling-chaos-http.conf.template /etc/nginx/sites-available/crawling-chaos.conf
sudo nano /etc/nginx/sites-available/crawling-chaos.conf
```

## Step 3: Customize Configuration

Edit the configuration file and replace:
- `DOMAIN_NAME` with your actual domain (e.g., `news.example.com`)
- SSL certificate paths (if using HTTPS)
- Upstream server address if needed (default: `localhost:5000`)

Example replacements:
```nginx
# Change this:
server_name DOMAIN_NAME;

# To this:
server_name news.example.com;

# And this (for HTTPS):
ssl_certificate /etc/letsencrypt/live/DOMAIN_NAME/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/DOMAIN_NAME/privkey.pem;

# To this:
ssl_certificate /etc/letsencrypt/live/news.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/news.example.com/privkey.pem;
```

## Step 4: Obtain SSL Certificate (HTTPS only)

Using Certbot for Let's Encrypt:
```bash
sudo certbot certonly --nginx -d news.example.com
```

Or using standalone mode if Nginx is not yet configured:
```bash
sudo systemctl stop nginx
sudo certbot certonly --standalone -d news.example.com
sudo systemctl start nginx
```

## Step 5: Enable the Site

```bash
# Create symbolic link to enable site
sudo ln -s /etc/nginx/sites-available/crawling-chaos.conf /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx
```

## Step 6: Verify Deployment

```bash
# Check Nginx status
sudo systemctl status nginx

# Test the application
curl https://news.example.com/api/health

# Check Nginx logs if issues occur
sudo tail -f /var/log/nginx/crawling-chaos-error.log
```

---

## Configuration Reference

### Rate Limiting

The Nginx configurations include rate limiting:

- **API endpoints**: 10 requests/second per IP (burst of 5)
- **General requests**: 30 requests/second per IP (burst of 20)

Adjust these in the configuration:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=general_limit:10m rate=30r/s;
```

### Load Balancing

To run multiple API instances for high availability:

1. Update `docker-compose.yaml` to run multiple API containers:
```yaml
api:
  deploy:
    replicas: 3
```

2. Update Nginx upstream configuration:
```nginx
upstream crawling_chaos_api {
    least_conn;  # or ip_hash for session persistence
    server localhost:5000;
    server localhost:5001;
    server localhost:5002;
}
```

### Custom Headers

Security headers are pre-configured. Customize in the server block:
```nginx
add_header Strict-Transport-Security "max-age=31536000" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header Content-Security-Policy "default-src 'self'" always;
```

### Caching

Static file caching is enabled by default (1 year):
```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

## Multi-Domain Server Integration

When running on a server with multiple domains:

### 1. Ensure Upstream Ports Don't Conflict

Each application should use different ports:
```
- news.example.com → localhost:5000 (Crawling Chaos)
- blog.example.com → localhost:3000 (Blog)
- api.example.com → localhost:8000 (Other API)
```

### 2. Organize Configuration Files

Keep one configuration file per domain:
```
/etc/nginx/sites-available/
├── crawling-chaos.conf
├── blog.example.com.conf
└── api.example.com.conf
```

### 3. Share SSL Configuration

Create a shared SSL configuration snippet:
```bash
# /etc/nginx/snippets/ssl-params.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
ssl_prefer_server_ciphers off;
```

Include in each site configuration:
```nginx
include snippets/ssl-params.conf;
```

---

## Monitoring and Maintenance

### View Nginx Access Logs

```bash
# Follow access log
sudo tail -f /var/log/nginx/crawling-chaos-access.log

# View error log
sudo tail -f /var/log/nginx/crawling-chaos-error.log
```

### Test Configuration Changes

Always test before reloading:
```bash
sudo nginx -t
```

### Reload Nginx Gracefully

```bash
sudo systemctl reload nginx
```

### Nginx Status Check

```bash
sudo systemctl status nginx
```

### Certificate Renewal

Let's Encrypt certificates auto-renew via cron. Test renewal:
```bash
sudo certbot renew --dry-run
```

---

## Troubleshooting

### 502 Bad Gateway

**Cause**: Nginx can't reach the backend application.

**Solutions**:
```bash
# Check if API is running
docker-compose ps

# Check if API is listening
curl http://localhost:5000/api/health

# Check Nginx error log
sudo tail -50 /var/log/nginx/crawling-chaos-error.log

# Verify upstream configuration
sudo nginx -T | grep -A 5 "upstream crawling_chaos_api"
```

### 504 Gateway Timeout

**Cause**: Request took too long to process.

**Solutions**:
- Increase timeout values in Nginx config:
```nginx
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
```

### SSL Certificate Issues

```bash
# Check certificate validity
sudo certbot certificates

# Verify certificate paths in Nginx config
sudo nginx -T | grep ssl_certificate

# Test SSL configuration
openssl s_client -connect news.example.com:443 -servername news.example.com
```

### Rate Limiting Issues

If legitimate users are being rate-limited:

1. Increase rate limits:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;
```

2. Or whitelist specific IPs:
```nginx
geo $limit {
    default 1;
    10.0.0.0/8 0;  # Internal network
    192.168.1.100 0;  # Specific IP
}

map $limit $limit_key {
    0 "";
    1 $binary_remote_addr;
}

limit_req_zone $limit_key zone=api_limit:10m rate=10r/s;
```

---

## Security Checklist

- [ ] HTTPS enabled with valid certificate
- [ ] HTTP redirects to HTTPS
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Hidden files (.env, .git) access denied
- [ ] Database port not exposed to public
- [ ] API keys stored in .env file (not committed to git)
- [ ] Firewall configured (only ports 80, 443 open)
- [ ] Regular updates applied to host system
- [ ] Nginx access/error logs monitored

---

## Performance Optimization

### Enable HTTP/2

Already enabled in HTTPS configuration:
```nginx
listen 443 ssl http2;
```

### Adjust Worker Processes

In main nginx.conf:
```nginx
worker_processes auto;
worker_connections 2048;
```

### Enable Caching (Optional)

Add proxy caching for API responses:
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=100m;

location /api/data/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    add_header X-Cache-Status $upstream_cache_status;

    proxy_pass http://crawling_chaos_api;
}
```

---

## Example: Complete Production Setup

Here's a complete workflow for setting up Crawling Chaos as `news.example.com` on a multi-domain server:

```bash
# 1. Deploy application
cd /opt/crawling-chaos
cp .env.example .env
nano .env  # Add API keys
docker-compose up -d

# 2. Copy and configure Nginx
sudo cp nginx/crawling-chaos.conf.template /etc/nginx/sites-available/news.example.com.conf
sudo sed -i 's/DOMAIN_NAME/news.example.com/g' /etc/nginx/sites-available/news.example.com.conf

# 3. Obtain SSL certificate
sudo certbot certonly --nginx -d news.example.com

# 4. Enable site
sudo ln -s /etc/nginx/sites-available/news.example.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 5. Create initial job
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d @api/templates/news_analysis_job.json

# 6. Start scheduler
curl -X POST http://localhost:5000/api/scheduler/start

# 7. Verify
curl https://news.example.com/api/health
```

Done! Your application is now running at `https://news.example.com`
