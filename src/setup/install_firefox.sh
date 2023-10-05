#!/usr/bin/env bash

# Check for the operating system
OS=$(uname)

install_firefox_linux() {
    if ! command -v firefox &> /dev/null; then
        echo "Firefox is not installed on Linux. Installing now..."
        sudo apt update
        sudo apt install -y firefox
    else
        echo "Firefox is already installed on Linux."
    fi
}

install_firefox_mac() {
    if ! brew list | grep -q firefox; then
        echo "Firefox is not installed on Mac. Installing now..."
        brew install firefox
    else
        echo "Firefox is already installed on Mac."
    fi
}

# Check and install based on OS
case "$OS" in
    "Linux")
        install_firefox_linux
        ;;
    "Darwin")  # macOS is identified by 'Darwin' in uname
        install_firefox_mac
        ;;
    *)
        echo "Unsupported operating system: $OS"
        ;;
esac
