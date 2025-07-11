from typing import Any, Dict, Optional

from ..exceptions import FabricSpecificationError, GaugeError, ValidationError
from ..models.knitting_models import FabricSpec, StitchPattern, YarnSpec
from .base_agent import AgentType, BaseAgent, Message


class FabricAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.FABRIC)
        self.gauge_map = {
            "worsted": {"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            "dk": {"stitches_per_inch": 5.0, "rows_per_inch": 6.0},
            "fingering": {"stitches_per_inch": 7.0, "rows_per_inch": 8.0},
        }

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make high-level fabric and material decisions"""
        try:
            # Validate input first
            if not self.validate_input(input_data):
                raise ValidationError(
                    "Invalid input data for fabric processing",
                    field="requirements",
                    expected="RequirementsSpec object",
                    value=input_data.get("requirements"),
                )

            requirements = input_data.get("requirements")

            # Determine yarn specifications
            yarn_spec = self._determine_yarn_requirements(requirements)

            # Select stitch pattern based on preferences
            stitch_pattern = self._select_stitch_pattern(requirements)

            # Choose border pattern if needed
            border_pattern = self._select_border_pattern(requirements)

            # Calculate gauge
            gauge = self._calculate_gauge(yarn_spec.weight)

            # Create construction notes
            construction_notes = self._create_construction_notes(
                requirements, stitch_pattern
            )

            # Validate the fabric specification before returning
            self._validate_fabric_spec(yarn_spec, stitch_pattern, gauge)

            fabric_spec = FabricSpec(
                stitch_pattern=stitch_pattern,
                border_pattern=border_pattern,
                yarn_requirements=yarn_spec,
                gauge=gauge,
                construction_notes=construction_notes,
            )

            return {"fabric_spec": fabric_spec}

        except (ValidationError, FabricSpecificationError, GaugeError):
            raise
        except Exception as e:
            raise FabricSpecificationError(
                f"Unexpected error during fabric specification: {str(e)}"
            ) from e

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data for fabric processing"""
        if not isinstance(input_data, dict):
            return False

        if "requirements" not in input_data:
            return False

        requirements = input_data["requirements"]
        # Check that requirements has the expected attributes
        return (
            hasattr(requirements, "style_preferences")
            and hasattr(requirements, "project_type")
            and hasattr(requirements, "dimensions")
        )

    def handle_message(self, message: Message) -> Dict[str, Any]:
        return {"status": "acknowledged"}

    def _determine_yarn_requirements(self, requirements) -> YarnSpec:
        """Determine yarn weight, fiber, and color"""
        # Default to worsted weight for now (could be made smarter based on project size, etc.)
        yarn_weight = "worsted"

        # Default to wool fiber (good for blankets)
        fiber = "wool"

        # Determine color based on style preferences
        color = self._determine_color(requirements)

        return YarnSpec(weight=yarn_weight, fiber=fiber, color=color)

    def _determine_color(self, requirements) -> Optional[str]:
        """Determine yarn color based on style preferences"""
        # For now, default to natural - could be enhanced for colorwork
        return "natural"

    def _select_stitch_pattern(self, requirements) -> StitchPattern:
        """Select appropriate stitch pattern based on preferences"""
        texture = requirements.style_preferences.get("texture", "simple")

        if texture == "cable":
            return StitchPattern(
                name="Simple Cable",
                row_repeat=8,
                stitch_repeat=12,
                instructions=[
                    "Row 1: *K4, C4F, K4; rep from *",
                    "Row 2 and all even rows: Purl",
                    "Row 3: Knit",
                    "Row 5: *K4, C4F, K4; rep from *",
                    "Row 7: Knit",
                ],
            )
        elif texture == "lace":
            return StitchPattern(
                name="Simple Lace",
                row_repeat=4,
                stitch_repeat=8,
                instructions=[
                    "Row 1: *K2, yo, k2tog, k2, ssk, yo; rep from *",
                    "Row 2: Purl",
                    "Row 3: *K1, yo, k2tog, k2, ssk, yo, k1; rep from *",
                    "Row 4: Purl",
                ],
            )
        else:
            return StitchPattern(
                name="Stockinette",
                row_repeat=2,
                stitch_repeat=1,
                instructions=["Row 1: Knit", "Row 2: Purl"],
            )

    def _select_border_pattern(self, requirements) -> StitchPattern:
        """Select border pattern for edges"""
        # All blankets get borders
        return StitchPattern(
            name="Seed Stitch Border",
            row_repeat=2,
            stitch_repeat=2,
            instructions=["Row 1: *K1, p1; rep from *", "Row 2: *P1, k1; rep from *"],
        )

    def _calculate_gauge(self, yarn_weight: str) -> Dict[str, float]:
        """Get gauge information for yarn weight"""
        try:
            if not yarn_weight:
                raise GaugeError(
                    "Cannot calculate gauge: yarn weight is empty",
                    yarn_weight=yarn_weight,
                )

            gauge = self.gauge_map.get(yarn_weight.lower())
            if gauge is None:
                # Return default gauge for unsupported weights
                supported_weights = list(self.gauge_map.keys())
                raise GaugeError(
                    f"Unsupported yarn weight: {yarn_weight}. "
                    f"Supported weights: {', '.join(supported_weights)}",
                    yarn_weight=yarn_weight,
                )

            return gauge

        except GaugeError:
            raise
        except Exception as e:
            raise GaugeError(
                f"Failed to calculate gauge: {str(e)}", yarn_weight=yarn_weight
            ) from e

    def _create_construction_notes(self, requirements, stitch_pattern) -> list[str]:
        """Create notes about construction decisions"""
        notes = []

        if stitch_pattern.name == "Simple Cable":
            notes.append("Cables provide structure and warmth")
            notes.append("Block finished piece to even out cable tension")
        elif stitch_pattern.name == "Simple Lace":
            notes.append("Lace creates drape and lightweight feel")
            notes.append("Consider using larger needles for more open fabric")
        else:
            notes.append("Stockinette creates smooth, classic fabric")
            notes.append("Consider adding garter stitch edges to prevent curling")

        return notes

    def _validate_fabric_spec(
        self,
        yarn_spec: YarnSpec,
        stitch_pattern: StitchPattern,
        gauge: Dict[str, float],
    ) -> None:
        """Validate the fabric specification for consistency"""
        # Validate yarn specification
        if not yarn_spec.weight or not yarn_spec.fiber:
            raise FabricSpecificationError(
                f"Incomplete yarn specification: weight={yarn_spec.weight}, fiber={yarn_spec.fiber}"
            )

        # Validate stitch pattern
        if not stitch_pattern.name or not stitch_pattern.instructions:
            raise FabricSpecificationError(
                f"Invalid stitch pattern: name={stitch_pattern.name}, instructions_count={len(stitch_pattern.instructions) if stitch_pattern.instructions else 0}"
            )

        if stitch_pattern.row_repeat <= 0 or stitch_pattern.stitch_repeat <= 0:
            raise FabricSpecificationError(
                f"Invalid stitch pattern repeats: row_repeat={stitch_pattern.row_repeat}, stitch_repeat={stitch_pattern.stitch_repeat}"
            )

        # Validate gauge
        if "stitches_per_inch" not in gauge or "rows_per_inch" not in gauge:
            raise GaugeError(f"Incomplete gauge information: {gauge}", gauge=gauge)

        stitches_per_inch = gauge["stitches_per_inch"]
        rows_per_inch = gauge["rows_per_inch"]

        if stitches_per_inch <= 0 or rows_per_inch <= 0:
            raise GaugeError(
                f"Invalid gauge values: stitches_per_inch={stitches_per_inch}, rows_per_inch={rows_per_inch}",
                gauge=gauge,
            )
