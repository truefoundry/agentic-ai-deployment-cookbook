import logging
import os

from dotenv import load_dotenv

load_dotenv(override=True)

from truefoundry.deploy import (
    Build,
    DockerFileBuild,
    LocalSource,
    NodeSelector,
    Port,
    Resources,
    Service,
)

logging.basicConfig(level=logging.INFO)

service = Service(
    name="test-crewai-fastapi-server",
    image=Build(
        build_source=LocalSource(local_build=False),
        build_spec=DockerFileBuild(
            dockerfile_path="./Dockerfile_crewai_agent_with_server",
            build_context_path="./",
        ),
    ),
    resources=Resources(
        cpu_request=0.5,
        cpu_limit=0.5,
        memory_request=1000,
        memory_limit=1000,
        ephemeral_storage_request=500,
        ephemeral_storage_limit=500,
        node=NodeSelector(capacity_type="spot_fallback_on_demand"),
    ),
    env={
        "LLM_MODEL_CREWAI": "openai/openai-main/gpt-4o",
        "LLM_MODEL_LANGCHAIN": "openai-main/gpt-4o",
        "LLM_GATEWAY_URL": "https://gateway.odsc-demo.truefoundry.cloud/v1",
        "TFY_API_KEY": os.getenv("TFY_API_KEY"),
    },
    ports=[
        Port(
            port=8000,
            protocol="TCP",
            expose=True,
            app_protocol="http",
            host="test-crewai-fastapi-server-sfhack-8000.ml.odsc-demo.truefoundry.cloud",
        )
    ],
    replicas=1.0,
)


service.deploy(workspace_fqn="odsc-cluster:sfhack", wait=False)
