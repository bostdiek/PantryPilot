"""Unit tests for the observability module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.observability import (
    ProductTelemetryEventName,
    _enable_pydantic_ai_instrumentation,
    _get_connection_string,
    _is_console_trace_exporter_enabled,
    _is_observability_enabled,
    _NoOpSpan,
    _NoOpTracer,
    build_product_telemetry_attributes,
    configure_observability,
    get_tracer,
    record_product_telemetry_event,
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


class TestConsoleTraceExporterEnabled:
    """Tests for local console trace exporter selection."""

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("console", True),
            ("otlp,console", True),
            ("CONSOLE", True),
            ("otlp", False),
            ("", False),
        ],
    )
    def test_console_exporter_detection(
        self,
        env_value: str,
        expected: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", env_value)
        assert _is_console_trace_exporter_enabled() is expected


class TestConfigureObservability:
    """Tests for configure_observability function."""

    def test_returns_false_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that False is returned when observability is disabled."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "false")
        # Clear the lru_cache to ensure fresh call
        configure_observability.cache_clear()
        result = configure_observability()
        assert result is False

    def test_does_not_enable_pydantic_ai_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test disabled startup does not initialize Pydantic AI instrumentation."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "false")
        configure_observability.cache_clear()

        with patch(
            "core.observability._enable_pydantic_ai_instrumentation"
        ) as mock_enable:
            result = configure_observability()
            assert result is False
            mock_enable.assert_not_called()

    def test_returns_false_when_no_connection_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that False is returned when connection string is missing."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "true")
        monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
        monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
        configure_observability.cache_clear()
        result = configure_observability()
        assert result is False

    def test_configures_console_exporter_without_connection_string(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test local console exporter configures spans without Azure secrets."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "true")
        monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
        monkeypatch.setenv("OTEL_SERVICE_NAME", "pantrypilot-backend-dev")
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
        configure_observability.cache_clear()

        events: list[str] = []
        mock_trace = MagicMock()
        mock_opentelemetry = MagicMock()
        mock_opentelemetry.trace = mock_trace
        mock_resource = MagicMock()
        mock_resource.create.side_effect = (
            lambda attrs: events.append(f"resource:{attrs['service.name']}")
            or "resource"
        )
        mock_provider = MagicMock()
        mock_provider_cls = MagicMock(return_value=mock_provider)
        mock_exporter_cls = MagicMock(return_value="exporter")
        mock_processor_cls = MagicMock(return_value="processor")
        mock_instrumentor = MagicMock()
        mock_instrumentor_cls = MagicMock(return_value=mock_instrumentor)
        mock_agent = MagicMock()
        mock_agent.instrument_all.side_effect = lambda: events.append("pydantic-ai")
        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = mock_agent

        monkeypatch.setattr("core.observability._pydantic_ai_instrumented", False)

        with patch.dict(
            "sys.modules",
            {
                "opentelemetry": mock_opentelemetry,
                "opentelemetry.sdk.resources": MagicMock(Resource=mock_resource),
                "opentelemetry.sdk.trace": MagicMock(TracerProvider=mock_provider_cls),
                "opentelemetry.sdk.trace.export": MagicMock(
                    ConsoleSpanExporter=mock_exporter_cls,
                    SimpleSpanProcessor=mock_processor_cls,
                ),
                "opentelemetry.instrumentation.fastapi": MagicMock(
                    FastAPIInstrumentor=mock_instrumentor_cls
                ),
                "pydantic_ai": mock_pydantic_ai,
            },
        ):
            result = configure_observability()

        assert result is True
        mock_provider_cls.assert_called_once_with(resource="resource")
        mock_provider.add_span_processor.assert_called_once_with("processor")
        mock_trace.set_tracer_provider.assert_called_once_with(mock_provider)
        mock_instrumentor.instrument.assert_called_once_with(
            excluded_urls="health,health/,favicon.ico"
        )
        mock_agent.instrument_all.assert_called_once_with()
        assert events == ["resource:pantrypilot-backend-dev", "pydantic-ai"]

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
        events: list[str] = []
        mock_configure = MagicMock()
        mock_configure.side_effect = lambda **_kwargs: events.append("azure")
        mock_module = MagicMock()
        mock_module.configure_azure_monitor = mock_configure
        mock_agent = MagicMock()
        mock_agent.instrument_all.side_effect = lambda: events.append("pydantic-ai")
        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = mock_agent

        monkeypatch.setattr("core.observability._pydantic_ai_instrumented", False)

        with patch.dict(
            "sys.modules",
            {
                "azure.monitor.opentelemetry": mock_module,
                "pydantic_ai": mock_pydantic_ai,
            },
        ):
            result = configure_observability()
            assert result is True
            mock_configure.assert_called_once()
            mock_agent.instrument_all.assert_called_once_with()
            assert events == ["azure", "pydantic-ai"]

    def test_returns_true_when_pydantic_ai_instrumentation_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test instrumentation failures are logged without failing startup."""
        monkeypatch.setenv("ENABLE_OBSERVABILITY", "true")
        monkeypatch.setenv(
            "APPLICATIONINSIGHTS_CONNECTION_STRING",
            "InstrumentationKey=test;IngestionEndpoint=https://test.com",
        )
        configure_observability.cache_clear()

        mock_configure = MagicMock()
        mock_module = MagicMock()
        mock_module.configure_azure_monitor = mock_configure
        mock_agent = MagicMock()
        mock_agent.instrument_all.side_effect = RuntimeError("instrumentation failed")
        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = mock_agent

        monkeypatch.setattr("core.observability._pydantic_ai_instrumented", False)

        with patch.dict(
            "sys.modules",
            {
                "azure.monitor.opentelemetry": mock_module,
                "pydantic_ai": mock_pydantic_ai,
            },
        ):
            result = configure_observability()
            assert result is True
            mock_configure.assert_called_once()
            mock_agent.instrument_all.assert_called_once_with()

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


class TestPydanticAiInstrumentation:
    """Tests for Pydantic AI observability integration."""

    def test_enable_pydantic_ai_instrumentation_is_idempotent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_agent = MagicMock()
        mock_pydantic_ai = MagicMock()
        mock_pydantic_ai.Agent = mock_agent

        monkeypatch.setattr("core.observability._pydantic_ai_instrumented", False)

        with patch.dict("sys.modules", {"pydantic_ai": mock_pydantic_ai}):
            _enable_pydantic_ai_instrumentation()
            _enable_pydantic_ai_instrumentation()

        mock_agent.instrument_all.assert_called_once_with()


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
        """Test that start_as_current_span yields a NoOpSpan as context manager."""
        tracer = _NoOpTracer()
        with tracer.start_as_current_span("test_span") as span:
            assert isinstance(span, _NoOpSpan)

    def test_start_span_returns_noop_span(self) -> None:
        """Test that start_span returns a NoOpSpan."""
        tracer = _NoOpTracer()
        span = tracer.start_span("test_span")
        assert isinstance(span, _NoOpSpan)

    def test_start_as_current_span_with_kwargs(self) -> None:
        """Test that start_as_current_span accepts kwargs."""
        tracer = _NoOpTracer()
        with tracer.start_as_current_span(
            "test_span", attributes={"key": "value"}
        ) as span:
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


class TestProductTelemetryContract:
    """Tests for metadata-only product telemetry contract helpers."""

    def test_build_attributes_includes_required_fields(self) -> None:
        attrs = build_product_telemetry_attributes(
            event=ProductTelemetryEventName.ASSISTANT_MESSAGE_STARTED,
            feature_name="assistant",
            request_id="req-123",
            conversation_id="conv-1",
            provider="google",
            model_name="gemini-3-flash-preview",
            streamed=True,
        )

        assert attrs["product.telemetry.event"] == "assistant_message_started"
        assert attrs["product.telemetry.feature_name"] == "assistant"
        assert attrs["product.telemetry.request_id"] == "req-123"
        assert attrs["product.telemetry.conversation_id"] == "conv-1"
        assert attrs["product.telemetry.provider"] == "google"
        assert attrs["product.telemetry.model_name"] == "gemini-3-flash-preview"
        assert attrs["product.telemetry.streamed"] is True

    def test_build_attributes_uses_context_correlation_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "core.observability.get_correlation_id",
            lambda: "corr-from-context",
        )

        attrs = build_product_telemetry_attributes(
            event=ProductTelemetryEventName.URL_IMPORT_FAILED,
            feature_name="ai_import",
            error_type="http_500",
            success=False,
        )

        assert attrs["product.telemetry.request_id"] == "corr-from-context"
        assert attrs["product.telemetry.error_type"] == "http_500"
        assert attrs["product.telemetry.success"] is False

    def test_build_attributes_joins_tool_names(self) -> None:
        attrs = build_product_telemetry_attributes(
            event=ProductTelemetryEventName.ASSISTANT_TOOL_COMPLETED,
            feature_name="assistant",
            request_id="req-456",
            tool_count=2,
            tool_names=["web_search", "fetch_url_as_markdown"],
        )

        assert attrs["product.telemetry.tool_count"] == 2
        assert (
            attrs["product.telemetry.tool_names"] == "web_search,fetch_url_as_markdown"
        )

    def test_record_event_keeps_event_name_off_span_attributes(self) -> None:
        span = MagicMock()

        attrs = record_product_telemetry_event(
            span,
            event=ProductTelemetryEventName.URL_IMPORT_COMPLETED,
            feature_name="url_import",
            request_id="req-789",
            success=True,
        )

        set_attribute_keys = [
            call.args[0] for call in span.set_attribute.call_args_list
        ]
        assert "product.telemetry.event" not in set_attribute_keys
        span.add_event.assert_called_once_with(
            "url_import_completed",
            attributes=attrs,
        )


class TestMainStartupObservabilityWiring:
    """Tests that app startup imports wire observability bootstrap."""

    def test_main_import_calls_configure_observability(self) -> None:
        import importlib

        import main

        with patch(
            "core.observability.configure_observability", return_value=False
        ) as mock_configure:
            importlib.reload(main)
            assert mock_configure.called

        importlib.reload(main)
