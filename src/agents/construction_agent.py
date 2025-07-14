from typing import Any, Dict, List

from ..exceptions import ConstructionPlanningError, ValidationError
from ..models.knitting_models import (
    ConstructionSpec,
    ConstructionZone,
    ProjectType,
)
from .base_agent import AgentType, BaseAgent, Message


class ConstructionAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.CONSTRUCTION)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Plan the structural construction of the project"""
        try:
            # Validate input first
            if not self.validate_input(input_data):
                raise ValidationError(
                    "Invalid input data for construction planning",
                    field="requirements or fabric_spec",
                    expected="RequirementsSpec and FabricSpec objects",
                    value=f"requirements={type(input_data.get('requirements'))}, fabric_spec={type(input_data.get('fabric_spec'))}",
                )

            requirements = input_data.get("requirements")
            fabric_spec = input_data.get("fabric_spec")

            # Validate requirements and fabric spec before planning
            self._validate_construction_inputs(requirements, fabric_spec)

            # Plan construction zones (borders, main body, etc.)
            construction_zones = self._plan_construction_zones(
                requirements, fabric_spec
            )

            # Determine construction sequence
            construction_sequence = self._plan_construction_sequence(
                requirements, construction_zones
            )

            # Plan finishing requirements
            finishing_requirements = self._plan_finishing_requirements(
                requirements, fabric_spec
            )

            # Generate structural notes
            structural_notes = self._generate_structural_notes(
                requirements, fabric_spec, construction_zones
            )

            # Validate the construction plan before creating spec
            self._validate_construction_plan(
                construction_zones, construction_sequence, finishing_requirements
            )

            construction_spec = ConstructionSpec(
                target_dimensions=requirements.dimensions,
                construction_zones=construction_zones,
                construction_sequence=construction_sequence,
                finishing_requirements=finishing_requirements,
                structural_notes=structural_notes,
            )

            return {"construction_spec": construction_spec}

        except (ValidationError, ConstructionPlanningError):
            raise
        except Exception as e:
            raise ConstructionPlanningError(
                f"Unexpected error during construction planning: {str(e)}"
            ) from e

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data for construction planning"""
        if not isinstance(input_data, dict):
            return False

        if "requirements" not in input_data or "fabric_spec" not in input_data:
            return False

        requirements = input_data["requirements"]
        fabric_spec = input_data["fabric_spec"]

        return (
            hasattr(requirements, "dimensions")
            and hasattr(requirements, "project_type")
            and hasattr(fabric_spec, "stitch_pattern")
            and hasattr(fabric_spec, "border_pattern")
        )

    def handle_message(self, message: Message) -> Dict[str, Any]:
        return {"status": "acknowledged"}

    def _plan_construction_zones(
        self, requirements, fabric_spec
    ) -> List[ConstructionZone]:
        """Plan the structural zones of the project"""
        try:
            zones = []

            # For blankets, we typically have border + main body
            if requirements.project_type == ProjectType.BLANKET:
                # Validate that we have valid stitch patterns
                if not fabric_spec.stitch_pattern:
                    raise ConstructionPlanningError(
                        "Cannot plan construction: missing main stitch pattern",
                        construction_type="zone_planning",
                    )

                # Border zone
                if fabric_spec.border_pattern:
                    if not fabric_spec.border_pattern.name:
                        raise ConstructionPlanningError(
                            "Invalid border pattern: missing name",
                            construction_type="border_planning",
                        )

                    border_zone = ConstructionZone(
                        name="border",
                        stitch_pattern=fabric_spec.border_pattern,
                        relative_position="perimeter",
                        priority=1,
                    )
                    zones.append(border_zone)

                # Main body zone
                if not fabric_spec.stitch_pattern.name:
                    raise ConstructionPlanningError(
                        "Invalid main stitch pattern: missing name",
                        construction_type="main_pattern_planning",
                    )

                main_zone = ConstructionZone(
                    name="main_body",
                    stitch_pattern=fabric_spec.stitch_pattern,
                    relative_position="center",
                    priority=2,
                )
                zones.append(main_zone)
            else:
                raise ConstructionPlanningError(
                    f"Unsupported project type for construction planning: {requirements.project_type}",
                    construction_type="project_type_validation",
                )

            if not zones:
                raise ConstructionPlanningError(
                    "No construction zones could be planned",
                    construction_type="zone_planning",
                )

            return zones

        except ConstructionPlanningError:
            raise
        except Exception as e:
            raise ConstructionPlanningError(
                f"Failed to plan construction zones: {str(e)}",
                construction_type="zone_planning",
            ) from e

    def _validate_construction_inputs(self, requirements, fabric_spec):
        """Validate requirements and fabric spec for construction planning"""
        if not requirements:
            raise ValidationError(
                "Missing requirements for construction planning",
                field="requirements",
                expected="RequirementsSpec object",
                value=None,
            )

        if not fabric_spec:
            raise ValidationError(
                "Missing fabric specification for construction planning",
                field="fabric_spec",
                expected="FabricSpec object",
                value=None,
            )

        if not hasattr(requirements, "dimensions") or not requirements.dimensions:
            raise ValidationError(
                "Missing dimensions in requirements",
                field="requirements.dimensions",
                expected="Dimensions object",
                value=getattr(requirements, "dimensions", None),
            )

        if not hasattr(requirements, "project_type"):
            raise ValidationError(
                "Missing project type in requirements",
                field="requirements.project_type",
                expected="ProjectType enum value",
                value=getattr(requirements, "project_type", None),
            )

        if not hasattr(fabric_spec, "stitch_pattern") or not fabric_spec.stitch_pattern:
            raise ValidationError(
                "Missing stitch pattern in fabric specification",
                field="fabric_spec.stitch_pattern",
                expected="StitchPattern object",
                value=getattr(fabric_spec, "stitch_pattern", None),
            )

    def _validate_construction_plan(
        self, construction_zones, construction_sequence, finishing_requirements
    ):
        """Validate the constructed plan before creating spec"""
        if not construction_zones:
            raise ConstructionPlanningError(
                "No construction zones planned",
                construction_type="plan_validation",
            )

        if not construction_sequence:
            raise ConstructionPlanningError(
                "No construction sequence planned",
                construction_type="plan_validation",
            )

        if not finishing_requirements:
            raise ConstructionPlanningError(
                "No finishing requirements planned",
                construction_type="plan_validation",
            )

        # Validate that zones have required attributes
        for zone in construction_zones:
            if not hasattr(zone, "name") or not zone.name:
                raise ConstructionPlanningError(
                    "Construction zone missing name",
                    construction_type="zone_validation",
                )

            if not hasattr(zone, "stitch_pattern") or not zone.stitch_pattern:
                raise ConstructionPlanningError(
                    f"Construction zone '{zone.name}' missing stitch pattern",
                    construction_type="zone_validation",
                )

    def _plan_construction_sequence(
        self, requirements, construction_zones
    ) -> List[str]:
        """Determine the order of construction steps"""
        sequence = ["cast_on"]

        # For blankets: borders (if any) -> main body -> finishing
        if requirements.project_type == ProjectType.BLANKET:
            # Check if we have borders
            has_border = any(zone.name == "border" for zone in construction_zones)

            if has_border:
                sequence.extend(
                    ["bottom_border", "main_body_with_side_borders", "top_border"]
                )
            else:
                sequence.append("main_body")

            sequence.extend(["bind_off", "finishing"])

        return sequence

    def _plan_finishing_requirements(self, requirements, fabric_spec) -> List[str]:
        """Determine what finishing steps are needed"""
        finishing = ["weave_in_ends"]

        # Always recommend blocking for blankets
        if requirements.project_type == ProjectType.BLANKET:
            finishing.append("blocking")

        # Add pattern-specific finishing
        pattern_name = fabric_spec.stitch_pattern.name
        if "Cable" in pattern_name:
            finishing.append("cable_blocking")
        elif "Lace" in pattern_name:
            finishing.append("aggressive_blocking")

        return finishing

    def _generate_structural_notes(
        self, requirements, fabric_spec, construction_zones
    ) -> List[str]:
        """Generate notes about the construction approach"""
        notes = []

        # Project size considerations
        area = requirements.dimensions.width * requirements.dimensions.length
        if area > 3000:  # Large blanket
            notes.append("Large project - consider using circular needles for comfort")
            notes.append("Work may become heavy - take breaks to avoid strain")

        # Pattern complexity notes
        main_pattern = fabric_spec.stitch_pattern.name
        if "Cable" in main_pattern:
            notes.append(
                "Cable pattern requires consistent tension for even appearance"
            )
            notes.append("Consider using cable needle or preferred cable method")

        # Border integration notes
        border_zones = [z for z in construction_zones if z.name == "border"]
        if border_zones:
            notes.append(
                "Border integrated into main construction - no separate pickup required"
            )
            notes.append("Maintain consistent edge tension for professional finish")

        # Construction method notes
        notes.append("Pattern worked flat in rows (not circular)")
        notes.append(
            "Right side rows are odd-numbered, wrong side rows are even-numbered"
        )

        return notes
