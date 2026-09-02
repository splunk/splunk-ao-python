"""SDK-owned batching lifecycle for completed OTel spans."""

from dataclasses import dataclass

from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

from splunk_ao.exporter.diagnostics import ExportHealth, get_export_health


@dataclass
class BatchConfig:
    """Configuration for the SDK-owned BatchSpanProcessor."""

    max_queue_size: int = 2048
    schedule_delay_millis: int = 5000
    export_timeout_millis: int = 30000
    max_export_batch_size: int = 512


class SpanSink:
    """SDK-owned abstraction over a batch processor and tracer provider."""

    def __init__(
        self, processor: BatchSpanProcessor, provider: TracerProvider, exporter: SpanExporter | None = None
    ) -> None:
        self._processor = processor
        self._provider = provider
        self._exporter = exporter
        self._shutdown = False

    @property
    def export_health(self) -> ExportHealth:
        """Return the current receiver-acknowledgement health snapshot."""
        return get_export_health(self._exporter)

    def emit(self, span: ReadableSpan) -> None:
        """Enqueue a completed span without flushing the batch."""
        if self._shutdown:
            raise RuntimeError("SpanSink is shut down")
        self._processor.on_end(span)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Drain all registered processors through the owned provider."""
        if self._shutdown:
            raise RuntimeError("SpanSink is shut down")
        return self._provider.force_flush(timeout_millis)

    def shutdown(self) -> None:
        """Shut down the owned provider exactly once."""
        if not self._shutdown:
            self._shutdown = True
            self._provider.shutdown()


def build_batch_processor(exporter: SpanExporter, config: BatchConfig | None = None) -> BatchSpanProcessor:
    """Build a BatchSpanProcessor with OTel defaults or explicit SDK configuration."""
    if config is None:
        return BatchSpanProcessor(exporter)

    return BatchSpanProcessor(
        exporter,
        max_queue_size=config.max_queue_size,
        schedule_delay_millis=config.schedule_delay_millis,
        export_timeout_millis=config.export_timeout_millis,
        max_export_batch_size=config.max_export_batch_size,
    )


def build_span_sink(exporter: SpanExporter, batch_config: BatchConfig | None = None) -> SpanSink:
    """Build an SDK-owned sink without replacing the global tracer provider."""
    processor = build_batch_processor(exporter, batch_config)
    provider = TracerProvider()
    provider.add_span_processor(processor)
    return SpanSink(processor, provider, exporter)
