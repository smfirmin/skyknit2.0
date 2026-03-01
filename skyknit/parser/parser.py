"""
LLM Pattern Parser — dataclasses, assembly helpers, and LLMPatternParser.

ParsedPattern (all Python primitives) is the boundary object between the
LLM JSON output and the deterministic schema types.  The private assembly
helpers convert it to typed ComponentIR / ShapeManifest / ConstraintObject,
which can then be passed directly to check_all() for validation.

PatternParser is a @runtime_checkable Protocol so tests can inject a
deterministic mock without importing the anthropic package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from skyknit.fabric.module import DeterministicFabricModule, FabricInput
from skyknit.parser.prompts import EXTRACT_TOOL_SCHEMA, SYSTEM_PROMPT
from skyknit.schemas.constraint import ConstraintObject, StitchMotif, YarnSpec
from skyknit.schemas.ir import ComponentIR, Operation, OpType
from skyknit.schemas.manifest import (
    ComponentSpec,
    Handedness,
    ShapeManifest,
    ShapeType,
)
from skyknit.schemas.proportion import PrecisionPreference
from skyknit.topology.types import Edge, EdgeType, Join, JoinType
from skyknit.utilities.conversion import row_count_to_physical, stitch_count_to_physical
from skyknit.utilities.types import Gauge

# ── Intermediate dataclasses (Python primitives only — no schema types) ────────


@dataclass(frozen=True)
class ParsedOperation:
    """Raw operation data extracted by the LLM, before type conversion."""

    op_type: str
    stitch_count_after: int | None
    row_count: int | None
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ParsedComponent:
    """Raw component data extracted by the LLM."""

    name: str
    handedness: str  # "LEFT" | "RIGHT" | "NONE"
    starting_stitch_count: int
    ending_stitch_count: int
    operations: tuple[ParsedOperation, ...]


@dataclass(frozen=True)
class ParsedJoin:
    """Raw join data extracted by the LLM."""

    id: str
    join_type: str
    edge_a_ref: str  # "component_name.edge_name"
    edge_b_ref: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ParsedPattern:
    """Full intermediate representation from the LLM before type conversion.

    Attributes:
        components: Ordered list of parsed component data.
        joins: Inter-component connections inferred from the pattern.
        gauge: (stitches_per_inch, rows_per_inch) if stated in pattern, else None.
        garment_type_hint: Best guess at garment type, or None.
    """

    components: tuple[ParsedComponent, ...]
    joins: tuple[ParsedJoin, ...]
    gauge: tuple[float, float] | None
    garment_type_hint: str | None


class ParseError(Exception):
    """Raised when the LLM response cannot be converted to a valid ParserOutput."""


# ── I/O dataclasses ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ParserInput:
    """Inputs for the pattern parser.

    Attributes:
        pattern_text: The raw knitting pattern text to parse.
        gauge: Gauge to use for dimension back-calculation.
        stitch_motif: Stitch pattern for constraint construction.
        yarn_spec: Yarn specification for constraint construction.
        precision: Tolerance precision preference.
    """

    pattern_text: str
    gauge: Gauge
    stitch_motif: StitchMotif
    yarn_spec: YarnSpec
    precision: PrecisionPreference = PrecisionPreference.MEDIUM


@dataclass(frozen=True)
class ParserOutput:
    """Complete typed output from the parser, ready for check_all().

    Attributes:
        parsed_pattern: Raw intermediate (useful for debugging LLM extraction).
        manifest: Assembled ShapeManifest for all components.
        irs: Mapping of component name → ComponentIR.
        constraints: Mapping of component name → ConstraintObject.
    """

    parsed_pattern: ParsedPattern
    manifest: ShapeManifest
    irs: dict[str, ComponentIR]
    constraints: dict[str, ConstraintObject]


@runtime_checkable
class PatternParser(Protocol):
    """Protocol for pattern parsers — allows deterministic test injection."""

    def parse(self, parser_input: ParserInput) -> ParserOutput: ...


# ── Private assembly helpers (all pure Python, no LLM) ───────────────────────


def _build_parsed_pattern(raw: dict[str, Any]) -> ParsedPattern:
    """Convert raw LLM JSON dict to a ParsedPattern of intermediate dataclasses."""
    components = tuple(
        ParsedComponent(
            name=c["name"],
            handedness=c.get("handedness", "NONE"),
            starting_stitch_count=int(c["starting_stitch_count"]),
            ending_stitch_count=int(c["ending_stitch_count"]),
            operations=tuple(
                ParsedOperation(
                    op_type=op["op_type"],
                    stitch_count_after=(
                        int(op["stitch_count_after"])
                        if op.get("stitch_count_after") is not None
                        else None
                    ),
                    row_count=(int(op["row_count"]) if op.get("row_count") is not None else None),
                    parameters=dict(op.get("parameters") or {}),
                )
                for op in c.get("operations", [])
            ),
        )
        for c in raw.get("components", [])
    )

    joins = tuple(
        ParsedJoin(
            id=j["id"],
            join_type=j["join_type"],
            edge_a_ref=j["edge_a_ref"],
            edge_b_ref=j["edge_b_ref"],
            parameters=dict(j.get("parameters") or {}),
        )
        for j in raw.get("joins", [])
    )

    raw_gauge = raw.get("gauge")
    gauge: tuple[float, float] | None = None
    if raw_gauge and isinstance(raw_gauge, dict):
        spi = raw_gauge.get("stitches_per_inch")
        rpi = raw_gauge.get("rows_per_inch")
        if spi is not None and rpi is not None:
            gauge = (float(spi), float(rpi))

    return ParsedPattern(
        components=components,
        joins=joins,
        gauge=gauge,
        garment_type_hint=raw.get("garment_type_hint"),
    )


def _infer_shape_type(comp: ParsedComponent) -> ShapeType:
    """Infer ShapeType from stitch count progression in the component's operations.

    If all non-zero stitch_count_after values are identical the component is
    a CYLINDER (uniform circumference).  Any variation signals TRAPEZOID.
    """
    non_zero_counts = [
        op.stitch_count_after
        for op in comp.operations
        if op.stitch_count_after is not None and op.stitch_count_after > 0
    ]
    if not non_zero_counts or len(set(non_zero_counts)) == 1:
        return ShapeType.CYLINDER
    return ShapeType.TRAPEZOID


def _infer_edges(
    comp: ParsedComponent,
    joins: tuple[ParsedJoin, ...],
) -> tuple[Edge, ...]:
    """Infer typed Edge objects for a component from its operations and joins.

    Rules (in order):

    First edge
    - First op is CAST_ON → CAST_ON edge named "neck".
    - Component is ``edge_b`` of any join → LIVE_STITCH edge with name + join_ref
      from the join ref string.
    - Fallback → LIVE_STITCH edge named "start".

    Last edge
    - Last op is BIND_OFF → BOUND_OFF edge; name is "cuff" for LEFT/RIGHT, "hem" otherwise.
    - Component is ``edge_a`` of a non-PICKUP join → LIVE_STITCH edge with name + join_ref.
    - Fallback → LIVE_STITCH edge named "end".

    SELVEDGE edges
    - For each PICKUP join where this component is ``edge_a``, append a SELVEDGE edge
      whose name is the edge-part of the join's ``edge_a_ref``.
    """
    first_op_type = comp.operations[0].op_type if comp.operations else None
    last_op_type = comp.operations[-1].op_type if comp.operations else None

    # Joins partitioned by this component's role
    downstream_joins = [j for j in joins if j.edge_b_ref.split(".")[0] == comp.name]
    upstream_joins = [j for j in joins if j.edge_a_ref.split(".")[0] == comp.name]
    pickup_source_joins = [j for j in upstream_joins if j.join_type == "PICKUP"]
    non_pickup_upstream = [j for j in upstream_joins if j.join_type != "PICKUP"]

    edges: list[Edge] = []

    # ── First edge ──────────────────────────────────────────────────────────────
    if first_op_type == "CAST_ON":
        edges.append(Edge(name="neck", edge_type=EdgeType.CAST_ON))
    elif downstream_joins:
        dj = downstream_joins[0]
        edge_name = dj.edge_b_ref.split(".", 1)[1]
        edges.append(Edge(name=edge_name, edge_type=EdgeType.LIVE_STITCH, join_ref=dj.id))
    else:
        edges.append(Edge(name="start", edge_type=EdgeType.LIVE_STITCH))

    # ── Last edge ───────────────────────────────────────────────────────────────
    if last_op_type == "BIND_OFF":
        last_name = "cuff" if comp.handedness in ("LEFT", "RIGHT") else "hem"
        edges.append(Edge(name=last_name, edge_type=EdgeType.BOUND_OFF))
    elif non_pickup_upstream:
        # Component feeds into a downstream component (CONTINUATION / HELD_STITCH)
        uj = non_pickup_upstream[0]
        edge_name = uj.edge_a_ref.split(".", 1)[1]
        edges.append(Edge(name=edge_name, edge_type=EdgeType.LIVE_STITCH, join_ref=uj.id))
    else:
        edges.append(Edge(name="end", edge_type=EdgeType.LIVE_STITCH))

    # ── SELVEDGE edges from PICKUP source joins ─────────────────────────────────
    for j in pickup_source_joins:
        edge_name = j.edge_a_ref.split(".", 1)[1]
        edges.append(Edge(name=edge_name, edge_type=EdgeType.SELVEDGE, join_ref=j.id))

    return tuple(edges)


def _back_calculate_dimensions(
    comp: ParsedComponent,
    shape_type: ShapeType,
    gauge: Gauge,
) -> dict[str, float]:
    """Back-calculate approximate physical dimensions from stitch/row counts.

    These are approximations derived from the parsed counts.  They feed
    ComponentSpec.dimensions but are not used by check_all() for arithmetic
    validation, so small deviations from the original measurements are harmless.

    For TRAPEZOID components that end in BIND_OFF (ending_stitch_count=0),
    the bottom circumference is derived from the last non-zero stitch count
    across all operations rather than ending_stitch_count itself.
    """
    total_rows = sum(op.row_count for op in comp.operations if op.row_count is not None)
    depth_mm = row_count_to_physical(total_rows, gauge)

    if shape_type == ShapeType.CYLINDER:
        return {
            "circumference_mm": stitch_count_to_physical(comp.starting_stitch_count, gauge),
            "depth_mm": depth_mm,
        }
    else:  # TRAPEZOID
        # Find last non-zero count (count before BIND_OFF if component is bound off)
        non_zero_counts = [
            op.stitch_count_after
            for op in comp.operations
            if op.stitch_count_after is not None and op.stitch_count_after > 0
        ]
        bottom_count = non_zero_counts[-1] if non_zero_counts else comp.ending_stitch_count
        return {
            "top_circumference_mm": stitch_count_to_physical(comp.starting_stitch_count, gauge),
            "bottom_circumference_mm": stitch_count_to_physical(bottom_count, gauge),
            "depth_mm": depth_mm,
        }


def _assemble_component_ir(comp: ParsedComponent) -> ComponentIR:
    """Convert a ParsedComponent to a typed ComponentIR.

    Raises ValueError if any op_type string is not a valid OpType member.

    For components whose first operation is PICKUP_STITCHES the VM starts with
    0 live stitches (before pick-up), so ``starting_stitch_count`` is forced to
    0 regardless of what the LLM reported.  This keeps the Algebraic Checker
    consistent with ``_exec_pickup_stitches``, which adds to the live count
    rather than setting it.
    """
    ops = tuple(
        Operation(
            op_type=OpType(op.op_type),  # raises ValueError on unrecognized string
            stitch_count_after=op.stitch_count_after,
            row_count=op.row_count,
            parameters=op.parameters,  # Operation.__post_init__ promotes dict → MappingProxyType
        )
        for op in comp.operations
    )
    first_op_type = comp.operations[0].op_type if comp.operations else None
    starting = 0 if first_op_type == "PICKUP_STITCHES" else comp.starting_stitch_count
    return ComponentIR(
        component_name=comp.name,
        handedness=Handedness(comp.handedness),
        operations=ops,
        starting_stitch_count=starting,
        ending_stitch_count=comp.ending_stitch_count,
    )


def _assemble_join(pj: ParsedJoin) -> Join:
    """Convert a ParsedJoin to a typed Join.

    Raises ValueError if join_type string is not a valid JoinType member.
    """
    return Join(
        id=pj.id,
        join_type=JoinType(pj.join_type),  # raises ValueError on unrecognized string
        edge_a_ref=pj.edge_a_ref,
        edge_b_ref=pj.edge_b_ref,
        parameters=pj.parameters,  # Join.__post_init__ promotes dict → MappingProxyType
    )


def _assemble_constraints(
    names: tuple[str, ...],
    gauge: Gauge,
    motif: StitchMotif,
    yarn: YarnSpec,
    precision: PrecisionPreference,
) -> dict[str, ConstraintObject]:
    """Build a ConstraintObject per component — mirrors DeterministicFabricModule."""
    fi = FabricInput(
        component_names=names,
        gauge=gauge,
        stitch_motif=motif,
        yarn_spec=yarn,
        precision=precision,
    )
    return DeterministicFabricModule().produce(fi).constraints


def _assemble(parsed: ParsedPattern, pi: ParserInput) -> ParserOutput:
    """Orchestrate conversion of ParsedPattern + ParserInput → typed ParserOutput."""
    joins = tuple(_assemble_join(pj) for pj in parsed.joins)

    component_specs: list[ComponentSpec] = []
    irs: dict[str, ComponentIR] = {}

    for comp in parsed.components:
        shape_type = _infer_shape_type(comp)
        edges = _infer_edges(comp, parsed.joins)
        dimensions = _back_calculate_dimensions(comp, shape_type, pi.gauge)

        spec = ComponentSpec(
            name=comp.name,
            shape_type=shape_type,
            dimensions=dimensions,  # ComponentSpec.__post_init__ promotes dict → MappingProxyType
            edges=edges,
            handedness=Handedness(comp.handedness),
            instantiation_count=1,
        )
        component_specs.append(spec)
        irs[comp.name] = _assemble_component_ir(comp)

    manifest = ShapeManifest(
        components=tuple(component_specs),
        joins=joins,
    )

    names = tuple(comp.name for comp in parsed.components)
    constraints = _assemble_constraints(
        names, pi.gauge, pi.stitch_motif, pi.yarn_spec, pi.precision
    )

    return ParserOutput(
        parsed_pattern=parsed,
        manifest=manifest,
        irs=irs,
        constraints=constraints,
    )


# ── LLMPatternParser ───────────────────────────────────────────────────────────


class LLMPatternParser:
    """Pattern parser backed by the Claude tool-use API.

    Uses ``tool_choice={"type": "any"}`` to force a ``tool_use`` response block,
    guaranteeing structured JSON output rather than free-text prose.

    Requires the ``anthropic`` package (``uv add anthropic`` or
    ``pip install skyknit[llm]``).  The import is deferred to ``__init__``
    so the rest of the module is importable without the package installed.

    The Anthropic client reads ``ANTHROPIC_API_KEY`` from the environment.
    """

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 4096,
    ) -> None:
        try:
            import anthropic

            self._client = anthropic.Anthropic()
        except ImportError as exc:
            raise ImportError(
                "Install the LLM extras for parser support: uv add anthropic"
            ) from exc
        self._model = model
        self._max_tokens = max_tokens

    def parse(self, pi: ParserInput) -> ParserOutput:
        """Parse pattern text into a typed ParserOutput via Claude tool-use."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=SYSTEM_PROMPT,
            tools=[EXTRACT_TOOL_SCHEMA],
            tool_choice={"type": "any"},
            messages=[
                {
                    "role": "user",
                    "content": "Parse this knitting pattern:\n\n" + pi.pattern_text,
                }
            ],
        )
        tool_block = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_block is None:
            raise ParseError("Claude did not return a tool_use block")
        try:
            parsed = _build_parsed_pattern(tool_block.input)
            return _assemble(parsed, pi)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ParseError(f"Failed to assemble parser output: {exc}") from exc
