from typing import Any, Dict, List

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
        requirements = input_data.get("requirements")
        fabric_spec = input_data.get("fabric_spec")

        # Plan construction zones (borders, main body, etc.)
        construction_zones = self._plan_construction_zones(requirements, fabric_spec)

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

        construction_spec = ConstructionSpec(
            target_dimensions=requirements.dimensions,
            construction_zones=construction_zones,
            construction_sequence=construction_sequence,
            finishing_requirements=finishing_requirements,
            structural_notes=structural_notes,
        )

        return {"construction_spec": construction_spec}

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return (
            "requirements" in input_data
            and "fabric_spec" in input_data
            and hasattr(input_data["requirements"], "dimensions")
        )

    def handle_message(self, message: Message) -> Dict[str, Any]:
        return {"status": "acknowledged"}

    def _plan_construction_zones(
        self, requirements, fabric_spec
    ) -> List[ConstructionZone]:
        """Plan the structural zones of the project"""
        zones = []

        # For blankets, we typically have border + main body
        if requirements.project_type == ProjectType.BLANKET:
            # Border zone
            if fabric_spec.border_pattern:
                border_zone = ConstructionZone(
                    name="border",
                    stitch_pattern=fabric_spec.border_pattern,
                    relative_position="perimeter",
                    priority=1,
                )
                zones.append(border_zone)

            # Main body zone
            main_zone = ConstructionZone(
                name="main_body",
                stitch_pattern=fabric_spec.stitch_pattern,
                relative_position="center",
                priority=2,
            )
            zones.append(main_zone)

        return zones

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
