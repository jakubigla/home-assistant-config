import sys
from pathlib import Path

# Add the flight_tracker package root to sys.path so tests can import modules directly
sys.path.insert(0, str(Path(__file__).parent.parent))
