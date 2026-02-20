"""Configuration module. Reads from .env file or environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

# Hue bridge settings
uri = os.environ.get('HUE_URI', '')
username = os.environ.get('HUE_USERNAME', '')
hue_token = os.environ.get('HUE_TOKEN', '')
selectedLamp = os.environ.get('HUE_LAMP', 'Desk Lamp')

# GPS coordinates
coordinates = [
    os.environ.get('LATITUDE', '0'),
    os.environ.get('LONGITUDE', '0')
]

# Lamp colors [brightness, hue, saturation]
rainColor = [120, 45000, 254]
snowColor = [120, 25000, 254]
defaultColor = [254, 10000, 0]
