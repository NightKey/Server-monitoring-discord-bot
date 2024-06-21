import requests
import urllib.parse
from dataclasses import dataclass

@dataclass()
class Coordinates:
    longitude: float
    latitude: float

def get_coordinates(address: str) -> Coordinates:
    print("Geolocation is collected from OpenStreetMap @ https://nominatim.openstreetmap.org/")
    url = 'https://nominatim.openstreetmap.org/search?q=' + urllib.parse.quote(address) +'&format=json&polygon=1&addressdetails=1'
    headers = {
        "User-Agent": "Night Key's Server Monitoring Discord Bot",
    }

    response = requests.get(url, headers=headers)
    response = response.json()
    return Coordinates(response[0]["lon"], response[0]["lat"])
