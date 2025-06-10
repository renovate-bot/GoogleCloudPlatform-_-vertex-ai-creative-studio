package common

import (
	"context"
	"log"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/sdk/resource"
	tracesdk "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.4.0"
)

// InitTracerProvider initializes and configures the OpenTelemetry tracer provider.
// It sets up a GRPC exporter to send trace data and configures the tracer with
// service name and version attributes. This is crucial for observability, allowing
// for distributed tracing of requests as they flow through the system.
func InitTracerProvider(serviceName, serviceVersion string) (*tracesdk.TracerProvider, error) {
	ctx := context.Background()

	exporter, err := otlptracegrpc.New(ctx)
	if err != nil {
		return nil, err
	}

	tr := tracesdk.NewTracerProvider(
		tracesdk.WithBatcher(exporter),
		tracesdk.WithResource(resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceNameKey.String(serviceName),
			semconv.ServiceVersionKey.String(serviceVersion),
		)),
	)

	otel.SetTracerProvider(tr)

	log.Printf("Tracer provider initialized for service: %s, version: %s", serviceName, serviceVersion)

	return tr, nil
}
