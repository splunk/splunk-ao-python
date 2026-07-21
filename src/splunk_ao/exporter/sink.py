"""SDK-owned batching lifecycle for completed OTel spans."""

from dataclasses import dataclass

from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter


@dataclass
class BatchConfig:
    """Configuration for the SDK-owned BatchSpanProcessor."""

    max_queue_size: int = 2048
    schedule_delay_millis: int = 5000
    export_timeout_millis: int = 30000
    max_export_batch_size: int = 512


class SpanSink:
    """SDK-owned abstraction over a batch processor and tracer provider."""

    def __init__(self, processor: BatchSpanProcessor, provider: TracerProvider) -> None:
        self._processor = processor
        self._provider = provider
        self._shutdown = False

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
    """Build a BatchSpanProcessor with explicit SDK defaults."""
    batch_config = config or BatchConfig()
    return BatchSpanProcessor(
        exporter,
        max_queue_size=batch_config.max_queue_size,
        schedule_delay_millis=batch_config.schedule_delay_millis,
        export_timeout_millis=batch_config.export_timeout_millis,
        max_export_batch_size=batch_config.max_export_batch_size,
    )


def build_span_sink(exporter: SpanExporter, batch_config: BatchConfig | None = None) -> SpanSink:
    """Build an SDK-owned sink without replacing the global tracer provider."""
    processor = build_batch_processor(exporter, batch_config)
    provider = TracerProvider()
    provider.add_span_processor(processor)
    return SpanSink(processor, provider)
