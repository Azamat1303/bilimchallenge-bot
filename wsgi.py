"""
Alwaysdata uchun WSGI kirish nuqtasi.

Alwaysdata konsolida "Sites" bo'limida yangi sayt yaratganda:
- Configuration: Python
- Command / WSGI file: /home/sizning-hisobingiz/bilimchallenge-api/wsgi.py

Bu fayl app.py dagi Flask ilovasini WSGI serveriga taqdim etadi.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import app as application

if __name__ == "__main__":
    application.run()
