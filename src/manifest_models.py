"""Pydantic models for `manifest.yaml` per ADR-006 + ADR-009.

Manifest is the single hardware↔edp-api contract artifact. It absorbs the
profile→asset mapping previously in `hardware_selector_map.yaml`.

Per ADR-012: in-file `version:` field is populated by semantic-release;
URL-versioning deferred until schema stabilizes (post step 6).
"""

from pydantic import BaseModel, Field

# Reason: variant keys are dashed (e.g. "commercial-ac") matching directory layout.
# Profile names are underscored (e.g. "commercial_ac") matching DeploymentProfile enum.


class GeometryUrls(BaseModel):
    """Per-equipment geometry URLs."""

    envelope: str
    vendor_step: str | None = None


class AssemblyVariant(BaseModel):
    """Per-variant assembly artifact URLs."""

    bom: str
    step: str
    glb: str
    glb_exploded: str | None = None  # webview artifact (top-open shell, parts moved)
    step_exploded: str | None = None  # FreeCAD-friendly exploded STEP with labels
    topology_yaml: str | None = None  # populated in step 6.6 for DTM generation


class PlateUrls(BaseModel):
    """Per-plate-id artifact URLs."""

    spec: str
    step: str
    dxf: str | None = None
    drawing_meta: str | None = None


class ProfileAssemblies(BaseModel):
    """Profile→asset selection. References ids/keys defined elsewhere in the manifest."""

    compute_container: str  # variant key, e.g. "commercial-ac"
    grid_container: str | None  # variant key or null for no_bess profiles
    interface_plates: list[str] = Field(default_factory=list)  # plate ids


class Manifest(BaseModel):
    """Top-level manifest schema."""

    version: str
    specs: dict[str, str] = Field(default_factory=dict)
    geometry: dict[str, GeometryUrls] = Field(default_factory=dict)
    assemblies: dict[str, dict[str, AssemblyVariant]] = Field(default_factory=dict)
    plates: dict[str, PlateUrls] = Field(default_factory=dict)
    profiles: dict[str, ProfileAssemblies] = Field(default_factory=dict)
