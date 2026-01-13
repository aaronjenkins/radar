#!/usr/bin/env python3
import os
import time
import logging
import requests
import meshtastic
import meshtastic.tcp_interface
from math import radians, sin, cos, sqrt, atan2
from typing import Optional, Iterable, Iterator
from fr24sdk.client import Client
from fr24sdk.models.flight import FlightSummaryLight

# =====================
# Config
# =====================
CENTER_LAT = lat_goes_here
CENTER_LON = long_goes_here
RADIUS_KM = 15
POLLING_SECONDS = 60

# FlightRadar24
API_TOKEN = os.environ.get("FR24_API_TOKEN")

# Meshtastic
MESH_IP = os.environ.get("MESH_IP")
MESH_CHANNEL_INDEX = int(os.environ.get("MESH_CHANNEL_INDEX", "2"))

# Basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Validate env
missing = []
if not API_TOKEN:
    missing.append("FR24_API_TOKEN")
if not MESH_IP:
    missing.append("MESH_IP")

if missing:
    raise SystemExit(f"Missing required environment variable(s): {', '.join(missing)}")

# =====================
# Geometry helpers
# =====================
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def is_inside_circle(flat: float, flon: float) -> bool:
    return haversine_km(flat, flon, CENTER_LAT, CENTER_LON) <= RADIUS_KM

def flights_in_circle(flights: Optional[Iterable[FlightSummaryLight]]) -> Iterator[FlightSummaryLight]:
    if not flights:
        return
        yield  # pragma: no cover (keeps it an iterator function)
    for flight in flights:
        lat = getattr(flight, "lat", None)
        lon = getattr(flight, "lon", None)
        if lat is not None and lon is not None and is_inside_circle(lat, lon):
            yield flight

# =====================
# Bounds helper
# =====================
def make_bounds(center_lat: float, center_lon: float, lat_delta: float = 1.0, lon_delta: float = 1.0) -> str:
    north = center_lat + lat_delta
    south = center_lat - lat_delta
    west = center_lon - lon_delta
    east = center_lon + lon_delta
    return f"{north},{south},{west},{east}"

BOUNDS = make_bounds(CENTER_LAT, CENTER_LON)

# =====================
# Alert state
# =====================
alerted: set[str] = set()

# =====================
# Message formatting
# =====================
def build_fr24_url(flight: FlightSummaryLight) -> str:
    """
    Build a FlightRadar24 URL. Best effort:
    - Prefer /{callsign}/{fr24_id} when both exist
    - Fall back to /{fr24_id}
    - Fall back to homepage
    """
    callsign = (getattr(flight, "callsign", None) or "").strip()
    fr24_id = getattr(flight, "fr24_id", None)

    if fr24_id and callsign:
        return f"https://www.flightradar24.com/{callsign}/{fr24_id}"
    if fr24_id:
        return f"https://www.flightradar24.com/{fr24_id}"
    return "https://www.flightradar24.com"

def format_alert(flight: FlightSummaryLight) -> str:
    callsign = (getattr(flight, "callsign", None) or "").strip() or "UNKNOWN"
    fr24_id = getattr(flight, "fr24_id", None) or "?"

    lat = getattr(flight, "lat", None)
    lon = getattr(flight, "lon", None)

    # Different SDKs vary on field names; try a couple.
    alt = getattr(flight, "alt", None)
    if alt is None:
        alt = getattr(flight, "altitude", None)

    spd = getattr(flight, "spd", None)
    if spd is None:
        spd = getattr(flight, "speed", None)

    url = build_fr24_url(flight)

    parts = [f"✈️ {callsign} entered area", f"id={fr24_id}"]
    if alt is not None:
        parts.append(f"alt={alt}")
    if spd is not None:
        parts.append(f"spd={spd}")
    if lat is not None and lon is not None:
        parts.append(f"{lat:.3f},{lon:.3f}")
    parts.append(url)

    # Keep reasonably compact for mesh
    return " | ".join(parts)

# =====================
# Meshtastic + combined alert
# =====================
def send_alert(iface: meshtastic.tcp_interface.TCPInterface, flight: FlightSummaryLight) -> None:
    msg = format_alert(flight)

    # Meshtastic (broadcast). wantAck=False to avoid MAX_RETRANSMIT spam on broadcasts.
    try:
        iface.sendText(
            msg,
            destinationId="^all",
            wantAck=False,
            channelIndex=MESH_CHANNEL_INDEX,
        )
        logging.info("Mesh alert sent on channel %d.", MESH_CHANNEL_INDEX)
    except Exception as exc:
        logging.error("Mesh send failed: %s", exc)


def process_alerts(iface: meshtastic.tcp_interface.TCPInterface, flights: Iterable[FlightSummaryLight]) -> None:
    for flight in flights:
        flight_id = getattr(flight, "fr24_id", None)
        if not flight_id:
            continue
        if flight_id in alerted:
            continue

        send_alert(iface, flight)
        alerted.add(flight_id)

def monitor_geofence() -> None:
    client = Client(api_token=API_TOKEN)
    iface = meshtastic.tcp_interface.TCPInterface(hostname=MESH_IP)
    time.sleep(2)  # small settle time so initial sync can complete

    try:
        while True:
            try:
                flights = client.live.flight_positions.get_light(
                    bounds=BOUNDS,
                    categories=["M", "D", "H"],
                )

                inside = list(flights_in_circle(getattr(flights, "data", None)))
                if inside:
                    process_alerts(iface, inside)

                time.sleep(POLLING_SECONDS)

            except Exception as exc:
                logging.error("Error during polling: %s", exc)
                time.sleep(POLLING_SECONDS)

    finally:
        iface.close()

if __name__ == "__main__":
    monitor_geofence()
