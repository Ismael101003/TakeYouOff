import json
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import app` works when running this script
proj_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(proj_root))

from app import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_geocode')

payload = {
    "origen": "Aeropuerto Felipe angeles",
    "destino": "Queretaro centro",
    "restricciones": ["Aeropuerto Toluca"]
}

with app.test_client() as client:
    resp = client.post('/api/optimize-route', json=payload)
    print('STATUS:', resp.status_code)
    text = resp.get_data(as_text=True)
    try:
        parsed = json.loads(text)
        print(json.dumps(parsed, indent=2, ensure_ascii=False)[:4000])
    except Exception:
        print('RAW RESPONSE:\n', text[:4000])

print('\nTest finished.')
