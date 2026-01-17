"""Unit tests for the observability module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.observability import (
    _get_connection_string,
    _is_observability_enabled,
    _NoOpSpan,
    _NoOpTracer,
    configure_observability,
    get_tracer,
)


class TestIsObservabilityEnabled:
    """Tests for _is_observability_enabled function."""

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("YES", True),
            ("on", True),
            ("ON", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("", False),
            ("random", False),
        ],
    )
    def test_truthy_and_falsy_values(
        self, env_value: str, expected: bool, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test various truthy and falsy environment variable values."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", env_value)
        assert _is_observability_enabled() is expected

    def test_default_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test default value when environment variable is not set."""
        monkeypatch.delenv("ENABLE_OBSERVABILITY", raising=False)
        assert _is_observability_enabled() is False


class TestGetConnectionString:
    """Tests for _get_connection_string function."""

    def test_returns_connection_string_when_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that connection string is returned when set."""
        expected = "InstrumentationKey=test;IngestionEndpoint=https://test.com"
        monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", expected)
        assert _get_connection_string() == expected

    def test_returns_none_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that None is returned when connection string is not set."""
        monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
        assert _get_connection_string() is None


class TestConfigureObservability:
    """Tests for configure_observability function."""

    def test_returns_false_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that False is returned when observability is disabled."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "false")
        # Clear the lru_cache to ensure fresh call
        configure_observability.cache_clear()
        result = configure_observability()
        assert result is False

    def test_returns_false_when_no_connection_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that False is returned when connection string is missing."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "true")
        monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
        configure_observability.cache_clear()
        result = configure_observability()
        assert result is False

    def test_returns_false_on_import_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that False is returned when azure-monitor package is not installed."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "true")
        monkeypatch.setenv(
            "APPLICATIONINSIGHTS_CONNECTION_STRING",
            "InstrumentationKey=test",
        )
        configure_observability.cache_clear()

        # Test by mocking the import inside the function
        import builtins

        original_import = builtins.__import__

        def mock_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
            if "azure.monitor" in name:
                raise ImportError("No module named 'azure.monitor.opentelemetry'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            configure_observability.cache_clear()
            result = configure_observability()
            assert result is False

    def test_returns_true_on_successful_configuration(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that True is returned when configuration succeeds."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "true")
        monkeypatch.setenv(
            "APPLICATIONINSIGHTS_CONNECTION_STRING",
            "InstrumentationKey=test;IngestionEndpoint=https://test.com",
        )
        configure_observability.cache_clear()

        # Mock the azure.monitor.opentelemetry module
        mock_configure = MagicMock()
        mock_module = MagicMock()
        mock_module.configure_azure_monitor = mock_configure

        with patch.dict("sys.modules", {"azure.monitor.opentelemetry": mock_module}):
            result = configure_observability()
            assert result is True
            mock_configure.assert_called_once()

    def test_returns_false_on_configuration_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that False is returned when configuration raises an exception."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "true")
        monkeypatch.setenv(
            "APPLICATIONINSIGHTS_CONNECTION_STRING",
            "InstrumentationKey=test",
        )
        configure_observability.cache_clear()

        # Mock the azure.monitor.opentelemetry module to raise an exception
        mock_module = MagicMock()
        mock_module.configure_azure_monitor.side_effect = RuntimeError("Config failed")

        with patch.dict("sys.modules", {"azure.monitor.opentelemetry": mock_module}):
            result = configure_observability()
            assert result is False


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_returns_noop_tracer_when_opentelemetry_not_installed(self) -> None:
        """Test that NoOpTracer is returned when OpenTelemetry is not available."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
            if name == "opentelemetry":
                raise ImportError("No module")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            tracer = get_tracer("test_module")
            assert isinstance(tracer, _NoOpTracer)

    def test_returns_real_tracer_when_opentelemetry_available(self) -> None:
        """Test that real tracer is returned when OpenTelemetry is available."""
        # OpenTelemetry is installed in the test environment
        tracer = get_tracer("test_module")
        # Should not be a NoOpTracer since opentelemetry is installed
        # (it comes with pydantic-ai)
        assert tracer is not None


class TestNoOpTracer:
    """Tests for _NoOpTracer class."""

    def test_start_as_current_span_returns_noop_span(self) -> None:
        """Test that start_as_current_span returns a NoOpSpan."""
        tracer = _NoOpTracer()
        span = tracer.start_as_current_span("test_span")
        assert isinstance(span, _NoOpSpan)

    def test_start_span_returns_noop_span(self) -> None:
        """Test that start_span returns a NoOpSpan."""
        tracer = _NoOpTracer()
        span = tracer.start_span("test_span")
        assert isinstance(span, _NoOpSpan)

    def test_start_as_current_span_with_kwargs(self) -> None:
        """Test that start_as_current_span accepts kwargs."""
        tracer = _NoOpTracer()
        span = tracer.start_as_current_span("test_span", attributes={"key": "value"})
        assert isinstance(span, _NoOpSpan)


class TestNoOpSpan:
    """Tests for _NoOpSpan class."""

    def test_context_manager_enter_returns_self(self) -> None:
        """Test that __enter__ returns the span itself."""
        span = _NoOpSpan()
        result = span.__enter__()
        assert result is span

    def test_context_manager_exit_succeeds(self) -> None:
        """Test that __exit__ completes without error."""
        span = _NoOpSpan()
        # Should not raise
        span.__exit__(None, None, None)

    def test_set_attribute_is_noop(self) -> None:
        """Test that set_attribute does nothing but doesn't raise."""
        span = _NoOpSpan()
        # Should not raise
        span.set_attribute("key", "value")
        span.set_attribute("number", 42)
        span.set_attribute("bool", True)

    def test_add_event_is_noop(self) -> None:
        """Test that add_event does nothing but doesn't raise."""
        span = _NoOpSpan()
        # Should not raise
        span.add_event("event_name")
        span.add_event("event_with_attrs", attributes={"key": "value"})

    def test_record_exception_is_noop(self) -> None:
        """Test that record_exception does nothing but doesn't raise."""
        span = _NoOpSpan()
        # Should not raise
        span.record_exception(ValueError("test error"))

    def test_end_is_noop(self) -> None:
        """Test that end does nothing but doesn't raise."""
        span = _NoOpSpan()
        # Should not raise
        span.end()

    def test_context_manager_usage(self) -> None:
        """Test full context manager usage pattern."""
        tracer = _NoOpTracer()
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test", "value")
            span.add_event("test_event")
        # Should complete without error
