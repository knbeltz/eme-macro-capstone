"""Local credentials; process environment takes precedence over the project .env."""
import os
from pathlib import Path
import re
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / '.env'
FRED_KEY_PATTERN = re.compile(r'[a-z0-9]{32}')


def get_fred_api_key(env_file=ENV_FILE):
    """Return the configured key without logging it or evaluating shell code."""
    if 'FRED_API_KEY' in os.environ:
        return os.environ['FRED_API_KEY'].strip() or None
    path = Path(env_file)
    if not path.exists():
        return None
    value = None
    for line in path.read_text().splitlines():
        match = re.match(r'^\s*(?:export\s+)?FRED_API_KEY\s*=\s*(.*?)\s*$', line)
        if match:
            candidate = match[1]
            if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in "\"'":
                candidate = candidate[1:-1]
            value = candidate.strip() or None
    return value


def save_fred_api_key(key, env_file=ENV_FILE):
    """Replace only FRED_API_KEY and atomically save with owner-only permissions."""
    key = key.strip()
    if not FRED_KEY_PATTERN.fullmatch(key):
        raise ValueError('FRED keys must contain 32 lowercase letters or digits.')
    path = Path(env_file)
    if path.is_symlink():
        raise ValueError('Refusing to replace a symlinked credentials file.')
    lines = path.read_text().splitlines() if path.exists() else []
    lines = [line for line in lines if not re.match(r'^\s*(?:export\s+)?FRED_API_KEY\s*=', line)]
    lines.append(f'FRED_API_KEY={key}')
    descriptor, temporary = tempfile.mkstemp(prefix='.env-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as handle:
            handle.write('\n'.join(lines) + '\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

