import logging

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
    name="test-mcp-server",
    image=Build(
        build_source=LocalSource(local_build=False),
        build_spec=DockerFileBuild(
            dockerfile_path="./Dockerfile_simple_mcp_server", build_context_path="./"
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
    env={"KEY": "VALUE"},
    ports=[
        Port(
            port=8000,
            protocol="TCP",
            expose=True,
            app_protocol="http",
            host="test-mcp-server-sfhack-8000.ml.odsc-demo.truefoundry.cloud",
        )
    ],
    replicas=1.0,
)


service.deploy(workspace_fqn="odsc-cluster:sfhack", wait=False)
