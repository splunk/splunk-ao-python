import "dotenv/config";
import { generateText, tool } from "ai";
import { openai } from "@ai-sdk/openai";
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { Resource } from "@opentelemetry/resources";
import { ATTR_SERVICE_NAME } from "@opentelemetry/semantic-conventions";
import { z } from "zod";

const exporter = new OTLPTraceExporter({
  url:
    process.env.SPLUNK_AO_API_ENDPOINT ??
    "https://api.galileo.ai/otel/v1/traces",
  headers: {
    "Splunk-AO-API-Key": process.env.SPLUNK_AO_API_KEY!,
    project: process.env.SPLUNK_AO_PROJECT!,
    logstream: process.env.SPLUNK_AO_AGENT_STREAM!,
  },
});

const sdk = new NodeSDK({
  traceExporter: exporter,
  resource: new Resource({
    [ATTR_SERVICE_NAME]: "vercel-ai-sdk-example",
  }),
});

sdk.start();

const result = await generateText({
  model: openai("gpt-4o-mini"),
  tools: {
    getWeather: tool({
      description: "Get the current weather for a location",
      parameters: z.object({
        location: z.string().describe("The city to get weather for"),
      }),
      execute: async ({ location }) => ({
        location,
        condition: ["sunny", "cloudy", "rainy", "windy"][
          Math.floor(Math.random() * 4)
        ],
        temperature_c: Math.floor(Math.random() * 26) + 10,
      }),
    }),
    getStockPrice: tool({
      description: "Get the current stock price for a ticker symbol",
      parameters: z.object({
        symbol: z.string().describe("The stock ticker symbol (e.g. AAPL)"),
      }),
      execute: async ({ symbol }) => {
        const prices: Record<string, number> = {
          AAPL: 178.5,
          GOOGL: 141.25,
          MSFT: 378.9,
          AMZN: 153.4,
        };
        return {
          symbol: symbol.toUpperCase(),
          price: prices[symbol.toUpperCase()] ?? 100.0,
          currency: "USD",
        };
      },
    }),
  },
  maxSteps: 5,
  prompt:
    "What's the weather in Tokyo and what's Apple's current stock price?",
  experimental_telemetry: {
    isEnabled: true,
    recordInputs: true,
    recordOutputs: true,
  },
});

console.log(result.text);

await sdk.shutdown();
