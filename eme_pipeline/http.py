import hashlib
import json
import logging
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

    def get(self, provider, country, url, params=None, headers=None, sensitive_params=()):
        # Authenticate on the wire, but keep credentials out of filenames, URLs,
        # response errors and tracebacks. Noncredentialed cache keys stay unchanged.
        secrets = [str((params or {})[name]) for name in sensitive_params
                   if (params or {}).get(name)]
        def redact(value):
            for secret in secrets:
                value = value.replace(secret, '[REDACTED]')
            return value
        safe_params = {name: ('[REDACTED]' if name in sensitive_params else value)
                       for name, value in (params or {}).items()}
        request = requests.Request('GET', url, params=safe_params if params else None).prepare()
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
        class RedactCredentials(logging.Filter):
            def filter(self, record):
                record.msg = redact(record.getMessage())
                record.args = ()
                return True
        log_filter = RedactCredentials()
        loggers = [logging.getLogger(name) for name in
                   ['urllib3.connectionpool','urllib3.util.retry','requests']] if secrets else []
        for logger in loggers:
            logger.addFilter(log_filter)
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=(10, 60))
            content = response.content
            for secret in secrets:
                content = content.replace(secret.encode(), b'[REDACTED]')
            body.write_bytes(content)
            m.update(status=response.status_code, final_url=redact(response.url),
                     content_type=response.headers.get('Content-Type'),
                     sha256=hashlib.sha256(content).hexdigest(),
                     credential_parameters_redacted=list(sensitive_params))
            response.raise_for_status()
            return content
        except requests.RequestException as exc:
            m['error'] = redact(str(exc))
            if sensitive_params:
                raise RuntimeError(m['error']) from None
            raise
        except KeyboardInterrupt:
            # Avoid exposing a credential-bearing requests exception context on Ctrl-C.
            raise KeyboardInterrupt('Request interrupted') from None
        finally:
            for logger in loggers:
                logger.removeFilter(log_filter)
            meta.write_text(json.dumps(m, indent=2))

    def json(self, *args, **kwargs):
        return json.loads(self.get(*args, **kwargs))
