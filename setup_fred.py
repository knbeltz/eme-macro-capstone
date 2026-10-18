"""Configure a local FRED key without placing it in chat or shell history."""
import argparse
import getpass
import os
import sys
import warnings

from eme_pipeline.settings import ENV_FILE, get_fred_api_key, save_fred_api_key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status', action='store_true', help='Check configuration without displaying the key or making an API call')
    args = parser.parse_args()
    if args.status:
        source = 'process environment' if 'FRED_API_KEY' in os.environ else str(ENV_FILE)
        print(f'FRED_API_KEY is configured ({source}).' if get_fred_api_key()
              else 'FRED_API_KEY is not configured. Run: .venv/bin/python setup_fred.py')
        print('This checks configuration only; API access has not been tested.')
        return
    if not sys.stdin.isatty():
        parser.exit(1, 'Run this command in your IDE terminal to use the hidden prompt.\n')
    print('Paste your FRED API key at the hidden prompt. Input will not be displayed.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            key = getpass.getpass('FRED API key: ')
        save_fred_api_key(key)
    except (ValueError, OSError, getpass.GetPassWarning) as exc:
        # Only validation/IO errors are shown; never echo the supplied value.
        parser.exit(1, f'Could not save the key: {exc}\n')
    except (EOFError, KeyboardInterrupt):
        parser.exit(1, '\nSetup cancelled.\n')
    print(f'Saved to {ENV_FILE} with owner-only permissions. The file is ignored by Git.')
    if 'FRED_API_KEY' in os.environ:
        print('An existing process environment variable takes precedence over this file.')
    print('API access has not been tested yet.')


if __name__ == '__main__':
    main()
