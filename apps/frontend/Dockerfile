# =============================================================================
# Frontend Dockerfile for PantryPilot React + Vite + Tailwind Application
# Based on Node.js + Vite + nginx best practices
# =============================================================================

# =============================================================================
# DEVELOPMENT STAGE
# =============================================================================
FROM node:20-alpine AS development

# Install system dependencies for development (git for some npm packages)
RUN apk add --no-cache git

# Set working directory
WORKDIR /app

# Copy package files first for better Docker layer caching
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies for development)
RUN npm ci --include=dev

# Copy the entire project
COPY . .

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001 -G nodejs

# Change ownership of the app directory
RUN chown -R nextjs:nodejs /app
USER nextjs

# Expose development port (Vite default)
EXPOSE 5173

# Development command with host binding for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# =============================================================================
# BUILD STAGE
# =============================================================================
FROM node:20-alpine AS builder

# Install system dependencies needed for building
RUN apk add --no-cache git

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install all dependencies for building
RUN npm ci --include=dev

# Copy source code
COPY . .

# Allow injecting the API base URL at build time (Vite picks up VITE_* env vars)
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

# Build the application for production
# TypeScript check + Vite build as per package.json script
RUN npm run build

# =============================================================================
# PRODUCTION STAGE
# =============================================================================
FROM nginx:1.25-alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration for React SPA
COPY <<EOF /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Handle client-side routing (React Router)
    location / {
        try_files \$uri \$uri/ /index.html;

        # Cache control for HTML files
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Additional security - deny access to hidden files (files starting with .)
    location ~ /\\. {
        deny all;
    }
}
EOF

# Set proper permissions for nginx files
RUN chmod 644 /etc/nginx/conf.d/default.conf && \
    chown -R nginx:nginx /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Expose port (internal only, not mapped in production)
EXPOSE 80

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
