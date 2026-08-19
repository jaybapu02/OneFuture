"""
Compatibility alias for the seed command (previously named seed_demo_data).

The actual seed command now lives in seed_data.py. Run:
    python manage.py seed_data
"""
from .seed_data import Command

__all__ = ["Command"]
