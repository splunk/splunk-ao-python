# CrewAI + Splunk AO Examples

This repo contains examples of how to use Splunk AO to instrument [CrewAI](https://www.crewai.com/) agents for observability and evaluation engineering.

## research_crew

The [resarch-crew](./research_crew/) is a quickstart tutorial. It is a completed version of the [CrewAI quickstart](https://docs.crewai.com/en/quickstart) and adds the
Splunk AO's [CrewAIEventListener](https://agent-observability-docs.splunk.com/sdk-api/python/reference/handlers/crewai/handler),
an event handler implemented on top of OpenTelemetry (OTel). For more information, see
Splunk AO’s [Add Splunk AO to a CrewAI Application](https://agent-observability-docs.splunk.com/how-to-guides/third-party-integrations/add-galileo-to-crewai/add-galileo-to-crewai)
how-to guide.

See the [README.md](./research_crew/README.md) for detailed setup instructions.
