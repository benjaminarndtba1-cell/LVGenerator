import re

from lvgenerator.constants import GAEBPhase, GAEB_DEFAULT_VERSION


_NS_PATTERN = re.compile(
    r"http://www\.gaeb\.de/GAEB_DA_XML/DA(\d{2})/([\d.]+)"
)


def get_namespace(phase: GAEBPhase, version: str = GAEB_DEFAULT_VERSION) -> str:
    return f"http://www.gaeb.de/GAEB_DA_XML/DA{phase.dp_value}/{version}"


def detect_phase_and_version(root) -> tuple[GAEBPhase, str]:
    tag = root.tag
    # lxml stores tags as {namespace}localname
    if tag.startswith("{"):
        ns_uri = tag[1:tag.index("}")]
    else:
        raise ValueError(f"Root element has no namespace: {tag}")

    match = _NS_PATTERN.match(ns_uri)
    if not match:
        raise ValueError(f"Unrecognized GAEB namespace: {ns_uri}")

    dp_value = int(match.group(1))
    version = match.group(2)
    phase = GAEBPhase.from_dp(dp_value)
    return phase, version
