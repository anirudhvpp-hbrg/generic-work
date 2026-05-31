"""Boot the cognitive engine onto the kernel.

Grants the default permissions the fleet needs and installs the concrete access
example from the architecture analysis: the commercial/standards agent (Aegis)
may touch pipeline data; the personal-redirection agent (Ira) may not.

``boot_shadow_os`` takes a Kernel and a Monarch instance (duck-typed: it only
reads ``monarch.fleet``), so the kernel package never imports the cognitive
layer — the dependency points one way, cognitive-on-resource.
"""

from __future__ import annotations


def boot_shadow_os(kernel, monarch):
    for shadow_id in monarch.fleet:
        kernel.access.grant(shadow_id, "execute")
        kernel.access.grant(shadow_id, "llm")
    kernel.access.grant("monarch", "execute")
    kernel.access.grant("monarch", "memory:write")

    # Access example: pipeline data is permitted to Aegis, denied to Ira.
    kernel.access.grant("aegis", "data:pipeline")
    kernel.tools.register(
        "pipeline_data",
        lambda: {"stage": "negotiation", "probability": 0.6},
        permission="data:pipeline",
    )
    return kernel
