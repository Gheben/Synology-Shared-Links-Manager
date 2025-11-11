# Synology Shared Links Manager

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg)

**A modern GUI application for managing Synology shared links permissions**

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support%20-yellow.svg?logo=buy-me-a-coffee&logoColor=white)](https://buymeacoffee.com/guidoballau)

</div>

## 📋 Description

Synology Shared Links Manager (SSLM) is a powerful desktop application that provides a modern graphical interface for managing shared links permissions on Synology NAS devices. It allows administrators to easily view, search, and modify group and user permissions for shared files and folders directly through SSH connection to the Synology database.

## ✨ Features

- **🔍 Advanced Search**: Search shared links by file/folder name with real-time filtering
- **👥 Group Management**: Add/remove specific groups or all groups from shared links
- **👤 User Management**: Add/remove specific users or all users from shared links
- **📊 Detailed Information**: View comprehensive details including owner, path, groups, users, and direct links
- **🔗 Quick Link Access**: One-click URL copying and browser opening
- **📝 Real-time Logging**: Detailed operation logs with success/error messages
- **🎨 Modern Interface**: Clean, professional GUI built with ttkbootstrap
- **⚡ Bulk Operations**: Perform actions on multiple selected records simultaneously
- **🔄 Auto-refresh**: Automatic UI updates after modifications

## 🖼️ Screenshot

<img width="1591" height="901" alt="image" src="https://github.com/user-attachments/assets/48b9e5d2-77c7-40f4-ba95-648be1c14791" />


*Modern interface with search results and detailed information panel*

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- SSH access to Synology NAS with administrator privileges
- Required Python packages (see requirements.txt)


### Method: Python Script (For developers)

1. Clone the repository:
```bash
git clone https://github.com/gheben/synology-shared-links-manager.git
cd synology-shared-links-manager
