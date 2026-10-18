import stat

import pytest

from eme_pipeline.settings import get_fred_api_key, save_fred_api_key


def test_credential_roundtrip_preserves_other_settings(tmp_path, monkeypatch):
    monkeypatch.delenv('FRED_API_KEY', raising=False)
    path = tmp_path / '.env'
    path.write_text('# Keep this comment\nOTHER_SETTING=unchanged\nFRED_API_KEY=old\n')
    key = 'a' * 32
    save_fred_api_key(key, path)
    assert get_fred_api_key(path) == key
    assert 'OTHER_SETTING=unchanged' in path.read_text()
    assert '# Keep this comment' in path.read_text()
    assert path.read_text().count('FRED_API_KEY=') == 1
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_environment_precedence_and_missing_key(tmp_path, monkeypatch):
    path = tmp_path / '.env'
    monkeypatch.delenv('FRED_API_KEY', raising=False)
    assert get_fred_api_key(path) is None
    path.write_text('FRED_API_KEY="' + 'a' * 32 + '"\n')
    monkeypatch.setenv('FRED_API_KEY', 'b' * 32)
    assert get_fred_api_key(path) == 'b' * 32
    monkeypatch.setenv('FRED_API_KEY', '')
    assert get_fred_api_key(path) is None


def test_invalid_key_does_not_change_file_or_echo_value(tmp_path):
    path = tmp_path / '.env'
    path.write_text('OTHER_SETTING=unchanged\n')
    invalid = 'invalid-secret\nOTHER=bad'
    with pytest.raises(ValueError) as exc:
        save_fred_api_key(invalid, path)
    assert invalid not in str(exc.value)
    assert path.read_text() == 'OTHER_SETTING=unchanged\n'
