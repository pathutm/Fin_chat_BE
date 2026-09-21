from opentelemetry import trace, metrics

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
    SpanExportResult
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader
)

from services.logging import create_telemetry_log

SERVICE_NAME = "finance-ai-chatbot-backend"

resource = Resource.create(
    {
        "service.name": SERVICE_NAME
    }
)


class SupabaseSpanExporter(SpanExporter):

    def export(self, spans):
        import asyncio

        async def save_spans():
            for span in spans:

                trace_id = format(
                    span.context.trace_id,
                    "032x"
                )

                span_id = format(
                    span.context.span_id,
                    "016x"
                )

                duration_ms = (
                    span.end_time - span.start_time
                ) / 1_000_000

                attributes = dict(
                    span.attributes
                )

                agent_name = attributes.get(
                    "agent.name"
                )

                model_used = attributes.get(
                    "model.name"
                )

                tool_name = attributes.get(
                    "tool.name"
                )

                if span.status.status_code.name == "ERROR":
                    status = "error"
                else:
                    status = "success"

                error_message = None

                if span.status.description:
                    error_message = str(
                        span.status.description
                    )

                if not error_message:
                    for event in span.events:
                        if event.name == "exception":
                            exception_attributes = dict(
                                event.attributes
                            )

                            error_message = (
                                exception_attributes.get(
                                    "exception.message"
                                )
                            )

                            if error_message:
                                error_message = str(
                                    error_message
                                )

                            break

                input_tokens = attributes.get(
                    "input.tokens"
                )

                output_tokens = attributes.get(
                    "output.tokens"
                )

                await create_telemetry_log(
                    trace_id=trace_id,
                    span_id=span_id,
                    operation=span.name,
                    agent_name=agent_name,
                    model_used=model_used,
                    duration_ms=duration_ms,
                    status=status,
                    error_message=error_message,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    tool_name=tool_name
                )

        try:
            asyncio.run(
                save_spans()
            )

            return SpanExportResult.SUCCESS

        except Exception as e:
            print(
                f"[Telemetry] Export failed: {e}"
            )

            return SpanExportResult.FAILURE

    def shutdown(self):
        return

    def force_flush(
        self,
        timeout_millis=30000
    ):
        return True


tracer_provider = TracerProvider(
    resource=resource
)

tracer_provider.add_span_processor(
    BatchSpanProcessor(
        SupabaseSpanExporter()
    )
)

trace.set_tracer_provider(
    tracer_provider
)

tracer = trace.get_tracer(
    "finance-ai-chatbot"
)


metric_reader = PeriodicExportingMetricReader(
    ConsoleMetricExporter()
)

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[
        metric_reader
    ]
)

metrics.set_meter_provider(
    meter_provider
)

meter = metrics.get_meter(
    "finance-ai-chatbot"
)


request_counter = meter.create_counter(
    "finance_ai_requests_total",
    description="Total number of chatbot requests"
)

mcp_counter = meter.create_counter(
    "finance_ai_mcp_requests_total",
    description="Total number of MCP requests"
)

mcp_error_counter = meter.create_counter(
    "finance_ai_mcp_errors_total",
    description="Total number of MCP errors"
)

request_duration = meter.create_histogram(
    "finance_ai_request_duration",
    description="Chatbot request duration"
)

input_token_counter = meter.create_counter(
    "finance_ai_input_tokens",
    description="Total input tokens"
)

output_token_counter = meter.create_counter(
    "finance_ai_output_tokens",
    description="Total output tokens"
)