#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Update package list and install software-properties-common if not installed
echo "Updating package list and installing prerequisites..."
apt-get update
apt-get install -y software-properties-common

# Add the Git PPA
echo "Adding Git PPA..."
add-apt-repository -y ppa:git-core/ppa

# Update package list to include the PPA packages
echo "Updating package list again after adding Git PPA..."
apt-get update

# Install or upgrade Git to the latest version
echo "Installing/upgrading Git..."
apt-get install -y git

# Verify the installation and print the Git version
echo "Git installation completed. Installed Git version:"
git --version
