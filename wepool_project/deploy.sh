#!/bin/bash
# Direct deployment from Codespaces to VPS

VPS_USER="root"
VPS_HOST="YOUR_VPS_IP"
PROJECT_DIR="/var/www/wepool"

echo "Deploying WePool directly from Codespaces..."

# Create tarball of project (excluding sensitive files)
echo "Creating project archive..."
tar --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='db.sqlite3' \
    -czf wepool_deploy.tar.gz .

# Transfer to VPS
echo "Transferring files to VPS..."
scp wepool_deploy.tar.gz $VPS_USER@$VPS_HOST:/tmp/

# SSH and extract
ssh $VPS_USER@$VPS_HOST << 'ENDSSH'
    echo "Setting up on VPS..."

    # Create directory
    sudo mkdir -p /var/www/wepool
    sudo chown $USER:$USER /var/www/wepool

    # Extract files
    cd /var/www/wepool
    tar -xzf /tmp/wepool_deploy.tar.gz
    rm /tmp/wepool_deploy.tar.gz

    echo "Files transferred successfully!"
ENDSSH

# Clean up local tarball
rm wepool_deploy.tar.gz

echo "Direct deployment completed!"
