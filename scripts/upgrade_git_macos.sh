#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Check if Homebrew is installed
if ! command -v brew &> /dev/null
then
    echo "Homebrew not found. Installing Homebrew first..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Update Homebrew
echo "Updating Homebrew..."
brew update

# Install or upgrade Git
echo "Installing/upgrading Git..."
brew install git || brew upgrade git

# Verify the installation and print the Git version
echo "Git installation completed. Installed Git version:"
git --version
