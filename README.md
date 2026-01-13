# Radar 

## Local Setup

1. Get a FlightRadar API Key ($9/month for the lowest tier) https://fr24api.flightradar24.com/subscriptions-and-credits
2. Get your mesh device connected to the same wifi as the server going to host this app, and get the device IP
3. Create a dedicated channel on your mesh device to send messages, and note the channel number
4. Get your Latitudate and Longitude (note: U.S. Longitudes start with a - sign)
5. Set your .env variables
   - FR24_API_TOKEN 
   - MESH_IP
   - MESH_CHANNEL_INDEX
6. create Python Virtual Environment
```
python3 -m venv radar
source cradar/bin/activate
```
7. install packages
   - `pip isntall meshtastic`
   - `pip install fr24sdk`



## Linux Service

```
[Unit]
Description=FlightRadar24 Geofence Alerts to Meshtastic
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/your_user/radar

ExecStart=/usr/bin/python3 /home/your_user/radar.py

# Environment variables
Environment="FR24_API_TOKEN=your_token_here"
Environment="MESH_IP=mesh_ip_here"
Environment="MESH_CHANNEL_INDEX=mesh_channel_index_here"

Restart=always
RestartSec=10

# Hardening (safe defaults)
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```
