# HTTPS Termination Setup Guide

This guide covers HTTPS/TLS termination options for PantryPilot deployments, targeting both Raspberry Pi and cloud environments.

## Overview

PantryPilot supports multiple approaches for SSL/TLS termination:

1. **Nginx TLS Termination** - Direct certificate management in nginx
2. **Let's Encrypt/Certbot** - Automated certificate management
3. **Cloudflare TLS** - Cloud-based TLS termination
4. **Reverse Proxy** - External load balancer/proxy handling TLS

## Option 1: Nginx TLS Termination (Self-Managed Certificates)

### Prerequisites
- Valid domain name pointing to your server
- SSL certificate and private key files

### Configuration

1. **Place certificates in the ssl directory:**
```bash
mkdir -p ssl/certs ssl/private
# Copy your certificate files
cp your-domain.crt ssl/certs/
cp your-domain.key ssl/private/
chmod 600 ssl/private/your-domain.key
```

2. **Update docker-compose.prod.yml:**
```yaml
nginx:
  ports:
    - "80:80"
    - "443:443"  # Enable HTTPS port
  volumes:
    - ./ssl/certs:/etc/ssl/certs:ro
    - ./ssl/private:/etc/ssl/private:ro
```

3. **Create nginx HTTPS configuration:**
```nginx
# Add to nginx/conf.d/default.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Enable HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Your existing location blocks here...
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## Option 2: Let's Encrypt with Certbot (Recommended for most setups)

### For Raspberry Pi / Self-Hosted

1. **Install Certbot:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Or using snap (recommended)
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

2. **Obtain certificate:**
```bash
# Stop nginx temporarily
sudo systemctl stop nginx

# Obtain certificate (standalone mode)
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Or use nginx plugin (if nginx is running)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

3. **Docker setup with Let's Encrypt:**
```yaml
# docker-compose.prod.yml
nginx:
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/conf.d:/etc/nginx/conf.d:ro
```

4. **Auto-renewal:**
```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab for auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet && docker compose restart nginx" | sudo crontab -
```

### For Cloud Deployment (with Certbot)

Use the same approach but ensure your cloud provider allows HTTP/HTTPS traffic:

```bash
# Example for AWS EC2 - ensure Security Groups allow ports 80 and 443
# Example for GCP - ensure firewall rules allow HTTP/HTTPS traffic
```

## Option 3: Cloudflare TLS (Recommended for public deployments)

### Advantages
- Automatic certificate management
- DDoS protection
- CDN benefits
- No server-side certificate management

### Setup

1. **Add domain to Cloudflare:**
   - Sign up at cloudflare.com
   - Add your domain
   - Update nameservers to Cloudflare's

2. **Configure SSL/TLS mode:**
   - Go to SSL/TLS tab in Cloudflare dashboard
   - Set to "Full (strict)" or "Full" mode
   - Enable "Always Use HTTPS"

3. **Origin certificates (for strict mode):**
```bash
# Generate origin certificate in Cloudflare dashboard
# Download and place in ssl/ directory
```

4. **Update environment variables:**
```bash
# .env.prod
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
VITE_API_URL=https://your-domain.com
```

5. **Nginx configuration for Cloudflare:**
```nginx
# Trust Cloudflare IPs
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
# ... (add all Cloudflare IP ranges)
real_ip_header CF-Connecting-IP;
```

## Option 4: External Reverse Proxy (AWS ALB, nginx proxy, etc.)

### For AWS Application Load Balancer

1. **Create ALB with SSL certificate:**
   - Use AWS Certificate Manager for free certificates
   - Configure ALB to forward to your EC2 instance on port 80

2. **Update security groups:**
   - ALB: Allow 443 from 0.0.0.0/0
   - EC2: Allow 80 from ALB security group only

3. **Docker configuration:**
```yaml
# No HTTPS port needed - ALB handles TLS termination
nginx:
  ports:
    - "80:80"
```

### For nginx Reverse Proxy

```nginx
# External nginx proxy configuration
upstream pantrypilot {
    server backend-server:80;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://pantrypilot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Security Considerations

### Certificate Security
- Store private keys with restricted permissions (600)
- Use strong passphrases for private keys
- Regularly rotate certificates
- Monitor certificate expiration

### TLS Configuration
- Use TLS 1.2 or higher only
- Disable weak ciphers
- Enable HSTS (Strict-Transport-Security header)
- Configure proper security headers

### Environment-Specific Notes

#### Raspberry Pi
- Consider using Let's Encrypt for automatic renewal
- Monitor resource usage with HTTPS
- Use hardware crypto acceleration if available

#### Cloud Deployment
- Leverage cloud provider SSL services when possible
- Use managed certificates (AWS ACM, GCP SSL certificates)
- Consider using CDN services (CloudFlare, AWS CloudFront)

## Testing HTTPS Setup

### Verify certificate installation:
```bash
# Test SSL certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Check certificate details
curl -vI https://your-domain.com
```

### Verify security headers:
```bash
# Check security headers
curl -I https://your-domain.com

# Online tools
# - SSL Labs SSL Server Test
# - Security Headers scanner
```

### Update application configuration:
```bash
# Update CORS origins in .env.prod
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Update frontend API URL
VITE_API_URL=https://your-domain.com
```

## Troubleshooting

### Common Issues

1. **Certificate not trusted:**
   - Verify certificate chain is complete
   - Check intermediate certificates

2. **Mixed content errors:**
   - Ensure all resources load via HTTPS
   - Update API URLs in frontend

3. **CORS errors after HTTPS:**
   - Update CORS_ORIGINS environment variable
   - Verify frontend is using HTTPS API URLs

4. **Certificate renewal fails:**
   - Check firewall rules for port 80
   - Verify DNS resolution
   - Check certbot logs

### Monitoring
- Set up monitoring for certificate expiration
- Monitor SSL/TLS handshake errors
- Track HTTPS usage and performance impact

## Recommended Approach by Environment

| Environment | Recommended Option | Reasoning |
|-------------|-------------------|-----------|
| **Raspberry Pi (Home)** | Let's Encrypt + Certbot | Free, automated, well-supported |
| **Raspberry Pi (Public)** | Cloudflare | Additional security and performance |
| **VPS/Dedicated Server** | Let's Encrypt + Certbot | Cost-effective, reliable |
| **AWS/GCP/Azure** | Cloud Provider SSL | Integrated, managed, scalable |
| **Enterprise** | Internal CA or Cloudflare | Control and compliance requirements |

Choose the option that best fits your infrastructure, security requirements, and maintenance capabilities.