# 📁 run.py
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Importer flask_app (pas app)
from api.views import flask_app

if __name__ == "__main__":
    print("🚀 COSMETIC PROTOCOL VALIDATOR - ENSET Challenge 2026")
    flask_app.run(debug=True, host="0.0.0.0", port=5000)