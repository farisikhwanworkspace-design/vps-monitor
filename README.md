# VPS Monitor Zahra

Web app untuk monitor VPS status dari phone.

## Features
- 📊 Real-time CPU, RAM, Disk, Network
- 🔌 Status semua services
- 🧹 Clean RAM button
- 🗑️ Clean Storage button
- 📱 Mobile-friendly (PWA)

## Install as App
1. Buka URL dari phone
2. Tekan "Add to Home Screen" (iOS) atau "Install" (Android)
3. App icon akan muncul dalam home screen

## API Endpoints
- `/api/cpu` - CPU usage
- `/api/ram` - RAM usage
- `/api/disk` - Disk usage
- `/api/net` - Network stats
- `/api/services` - Service status
- `/api/clean/ram` - Clean RAM (POST)
- `/api/clean/storage` - Clean storage (POST)
