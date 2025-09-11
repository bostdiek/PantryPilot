#!/bin/bash

# PantryPilot HTTPS Setup Helper Script
# This script helps manage HTTPS configuration for PantryPilot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NGINX_CONF_DIR="$PROJECT_ROOT/nginx/conf.d"

usage() {
    echo "Usage: $0 {enable|disable|status|help}"
    echo ""
    echo "Commands:"
    echo "  enable   - Enable HTTPS configuration (requires SSL certificates)"
    echo "  disable  - Disable HTTPS and use HTTP only"
    echo "  status   - Show current HTTPS configuration status"
    echo "  help     - Show this help message"
    echo ""
    echo "Before enabling HTTPS, ensure you have:"
    echo "1. Valid SSL certificates in ssl/certs/ and ssl/private/"
    echo "2. Updated domain name in nginx configuration"
    echo "3. Updated CORS_ORIGINS in environment files"
}

check_certificates() {
    local cert_dir="$PROJECT_ROOT/ssl/certs"
    local key_dir="$PROJECT_ROOT/ssl/private"
    
    if [[ ! -d "$cert_dir" ]] || [[ ! -d "$key_dir" ]]; then
        echo "Error: SSL directories not found"
        echo "Create directories: mkdir -p ssl/certs ssl/private"
        return 1
    fi
    
    if [[ ! -f "$cert_dir/pantrypilot.crt" ]] || [[ ! -f "$key_dir/pantrypilot.key" ]]; then
        echo "Warning: Default certificate files not found"
        echo "Expected files:"
        echo "  - ssl/certs/pantrypilot.crt"
        echo "  - ssl/private/pantrypilot.key"
        echo ""
        echo "You can use different filenames by updating the nginx configuration."
        return 1
    fi
    
    return 0
}

enable_https() {
    echo "Enabling HTTPS configuration..."
    
    # Check if certificates exist
    if ! check_certificates; then
        echo ""
        echo "Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "HTTPS configuration cancelled."
            exit 1
        fi
    fi
    
    # Backup current configuration
    if [[ -f "$NGINX_CONF_DIR/default.conf" ]]; then
        cp "$NGINX_CONF_DIR/default.conf" "$NGINX_CONF_DIR/default.conf.http.backup"
        echo "Backed up HTTP configuration to default.conf.http.backup"
    fi
    
    # Copy HTTPS template
    if [[ -f "$NGINX_CONF_DIR/https.conf.template" ]]; then
        cp "$NGINX_CONF_DIR/https.conf.template" "$NGINX_CONF_DIR/default.conf"
        echo "Enabled HTTPS configuration"
        
        echo ""
        echo "IMPORTANT: Update the following in nginx/conf.d/default.conf:"
        echo "1. Change 'server_name localhost;' to your domain name"
        echo "2. Update SSL certificate paths if different"
        echo "3. Update CORS_ORIGINS in .env files to use HTTPS URLs"
        echo ""
        echo "Then restart the containers: make down && make up"
    else
        echo "Error: HTTPS template not found at $NGINX_CONF_DIR/https.conf.template"
        exit 1
    fi
}

disable_https() {
    echo "Disabling HTTPS configuration..."
    
    # Restore HTTP backup if it exists
    if [[ -f "$NGINX_CONF_DIR/default.conf.http.backup" ]]; then
        cp "$NGINX_CONF_DIR/default.conf.http.backup" "$NGINX_CONF_DIR/default.conf"
        echo "Restored HTTP configuration from backup"
    else
        echo "Warning: No HTTP backup found. You may need to manually reconfigure."
    fi
    
    echo "Disabled HTTPS configuration"
    echo "Restart containers: make down && make up"
}

show_status() {
    echo "HTTPS Configuration Status:"
    echo ""
    
    if [[ -f "$NGINX_CONF_DIR/default.conf" ]]; then
        if grep -q "listen 443 ssl" "$NGINX_CONF_DIR/default.conf"; then
            echo "Status: HTTPS ENABLED"
            
            # Check server name
            local server_name
            server_name=$(grep "server_name" "$NGINX_CONF_DIR/default.conf" | head -1 | awk '{print $2}' | sed 's/;//')
            echo "Server name: $server_name"
            
            # Check certificate paths
            local cert_path
            local key_path
            cert_path=$(grep "ssl_certificate " "$NGINX_CONF_DIR/default.conf" | head -1 | awk '{print $2}' | sed 's/;//')
            key_path=$(grep "ssl_certificate_key" "$NGINX_CONF_DIR/default.conf" | head -1 | awk '{print $2}' | sed 's/;//')
            echo "Certificate: $cert_path"
            echo "Private key: $key_path"
            
            # Check if certificate files exist (in container context, we can't check actual files)
            echo ""
            echo "Certificate check:"
            if [[ -f "$PROJECT_ROOT/ssl/certs/pantrypilot.crt" ]]; then
                echo "✓ Certificate file found"
            else
                echo "✗ Certificate file not found"
            fi
            
            if [[ -f "$PROJECT_ROOT/ssl/private/pantrypilot.key" ]]; then
                echo "✓ Private key file found"
            else
                echo "✗ Private key file not found"
            fi
            
        else
            echo "Status: HTTP ONLY"
        fi
    else
        echo "Status: NO CONFIGURATION FOUND"
    fi
    
    echo ""
    echo "Backup files:"
    if [[ -f "$NGINX_CONF_DIR/default.conf.http.backup" ]]; then
        echo "✓ HTTP backup available"
    else
        echo "✗ No HTTP backup found"
    fi
}

case "${1:-}" in
    enable)
        enable_https
        ;;
    disable)
        disable_https
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "Error: Unknown command '${1:-}'"
        echo ""
        usage
        exit 1
        ;;
esac