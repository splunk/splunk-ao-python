from splunk_ao.utils.decorators import splunk_ao_logging_enabled


def test_splunk_ao_logging_enabled(monkeypatch) -> None:
    assert splunk_ao_logging_enabled() is True

    monkeypatch.setenv("SPLUNK_AO_LOGGING_DISABLED", "true")
    assert splunk_ao_logging_enabled() is False

    monkeypatch.setenv("SPLUNK_AO_LOGGING_DISABLED", "1")
    assert splunk_ao_logging_enabled() is False
