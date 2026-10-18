import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class Client:
    """Cache original bytes and a request manifest; failures are evidence too."""
    def __init__(self, root=Path('data/raw'), offline=False):
        self.root = Path(root)
        self.offline = offline
        self.session = requests.Session()
        self.session.mount('https://', HTTPAdapter(max_retries=Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
            respect_retry_after_header=True)))

    def get(self, provider, country, url, params=None, headers=None):
        request = requests.Request('GET', url, params=params).prepare()
        key = hashlib.sha256(request.url.encode()).hexdigest()[:20]
        folder = self.root / provider / country
        folder.mkdir(parents=True, exist_ok=True)
        body, meta = folder / (key + '.body'), folder / (key + '.json')
        if meta.exists() and body.exists():
            m = json.loads(meta.read_text())
            if m.get('status') == 200:
                cached=body.read_bytes()
                if hashlib.sha256(cached).hexdigest()!=m['sha256']:
                    raise ValueError(f'Cached response hash mismatch: {body}')
                return cached
        if self.offline:
            raise RuntimeError(f'No successful cached response: {request.url}')
        time.sleep(0.25)
        m = dict(url=request.url, retrieved_at=datetime.now(timezone.utc).isoformat(),
                 accept=(headers or {}).get('Accept','*/*'))
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=(10, 60))
            body.write_bytes(response.content)
            m.update(status=response.status_code, final_url=response.url,
                     content_type=response.headers.get('Content-Type'),
                     sha256=hashlib.sha256(response.content).hexdigest())
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            m['error'] = str(exc)
            raise
        finally:
            meta.write_text(json.dumps(m, indent=2))

    def json(self, *args, **kwargs):
        return json.loads(self.get(*args, **kwargs))
