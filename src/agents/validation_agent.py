from typing import Any, Dict

from .base_agent import AgentType, BaseAgent, Message


class ValidationAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.VALIDATION)
        self.tolerance = 0.5  # inches

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern accuracy and feasibility"""
        fabric_spec = input_data.get("fabric_spec")
        stitch_result = input_data.get("stitch_result")
        requirements = input_data.get("requirements")

        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

        # Add dimension validation to stitch_result
        dimension_validation = self._validate_dimension_accuracy(
            requirements, stitch_result["actual_dimensions"]
        )
        stitch_result["dimension_validation"] = dimension_validation

        # Run validation checks
        self._validate_stitch_math(
            requirements, fabric_spec, stitch_result, validation_results
        )
        self._validate_yarn_requirements(requirements, fabric_spec, validation_results)
        self._validate_pattern_logic(fabric_spec, stitch_result, validation_results)
        self._validate_skill_level_consistency(fabric_spec, validation_results)
        self._validate_construction_feasibility(
            requirements, fabric_spec, validation_results
        )

        # Overall validation status
        validation_results["is_valid"] = len(validation_results["errors"]) == 0

        return {"validation": validation_results}

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return (
            "fabric_spec" in input_data
            and "construction_spec" in input_data
            and "stitch_result" in input_data
            and "requirements" in input_data
        )

    def handle_message(self, message: Message) -> Dict[str, Any]:
        return {"status": "acknowledged"}

    def _validate_stitch_math(self, requirements, fabric_spec, stitch_result, results):
        """Validate stitch calculations are mathematically correct"""

        # Check cast-on calculation
        expected_width = (
            stitch_result["cast_on_stitches"] / fabric_spec.gauge["stitches_per_inch"]
        )
        target_width = requirements.dimensions.width

        if abs(expected_width - target_width) > self.tolerance:
            results["errors"].append(
                f"Width calculation error: {stitch_result['cast_on_stitches']} stitches "
                f'will produce {expected_width:.1f}" but target is {target_width:.1f}"'
            )

        # Check row calculation
        expected_length = (
            stitch_result["total_rows"] / fabric_spec.gauge["rows_per_inch"]
        )
        target_length = requirements.dimensions.length

        if abs(expected_length - target_length) > self.tolerance:
            results["errors"].append(
                f"Length calculation error: {stitch_result['total_rows']} rows "
                f'will produce {expected_length:.1f}" but target is {target_length:.1f}"'
            )

        # Check for impossible stitch counts
        if stitch_result["cast_on_stitches"] <= 0:
            results["errors"].append("Cast-on stitch count must be positive")

        if stitch_result["total_rows"] <= 0:
            results["errors"].append("Total row count must be positive")

    def _validate_yarn_requirements(self, requirements, fabric_spec, results):
        """Validate yarn requirements are reasonable"""
        yarn = fabric_spec.yarn_requirements
        requirements.dimensions.width * requirements.dimensions.length

        # Note: Yarn yardage validation will be done in output agent where yardage is calculated

        # Check gauge matches yarn weight
        gauge = fabric_spec.gauge["stitches_per_inch"]
        expected_gauges = {
            "fingering": (6, 8),
            "dk": (4.5, 6),
            "worsted": (3.5, 5),
            "chunky": (2, 4),
        }

        if yarn.weight in expected_gauges:
            min_gauge, max_gauge = expected_gauges[yarn.weight]
            if not (min_gauge <= gauge <= max_gauge):
                results["warnings"].append(
                    f"Gauge {gauge} sts/inch may be unusual for {yarn.weight} weight yarn "
                    f"(typical range: {min_gauge}-{max_gauge} sts/inch)"
                )

    def _validate_pattern_logic(self, fabric_spec, stitch_result, results):
        """Validate pattern construction logic"""

        # Check stitch pattern repeats work with cast-on count
        pattern = fabric_spec.stitch_pattern
        cast_on = stitch_result["cast_on_stitches"]

        if pattern.stitch_repeat > 1:
            # Account for border stitches if present
            pattern_stitches = cast_on
            if fabric_spec.border_pattern:
                pattern_stitches -= 8  # Subtract border stitches

            if pattern_stitches % pattern.stitch_repeat != 0:
                results["errors"].append(
                    f"Stitch pattern repeat ({pattern.stitch_repeat} sts) doesn't divide evenly "
                    f"into pattern area ({pattern_stitches} sts)"
                )

        # Check row pattern repeats
        total_rows = stitch_result["total_rows"]
        if pattern.row_repeat > 1 and total_rows % pattern.row_repeat != 0:
            results["suggestions"].append(
                f"Consider adjusting length so total rows ({total_rows}) is divisible "
                f"by pattern repeat ({pattern.row_repeat} rows) for complete pattern"
            )

        # Note: Border compatibility validation moved to construction feasibility

    def _validate_skill_level_consistency(self, fabric_spec, results):
        """Check if pattern complexity matches intended skill level"""
        pattern_name = fabric_spec.stitch_pattern.name
        yarn_weight = fabric_spec.yarn_requirements.weight

        # Define complexity levels
        intermediate_patterns = ["Simple Cable", "Simple Lace"]
        advanced_patterns = ["Complex Cable", "Complex Lace"]

        # Check for skill mismatches
        if pattern_name in intermediate_patterns and yarn_weight == "fingering":
            results["warnings"].append(
                "Fingering weight yarn with intermediate patterns may be challenging - "
                "consider DK or worsted for easier handling"
            )

        if pattern_name in advanced_patterns and yarn_weight == "chunky":
            results["warnings"].append(
                "Advanced patterns may not show well in chunky yarn - "
                "consider finer weights for better pattern definition"
            )

    def _validate_construction_feasibility(self, requirements, fabric_spec, results):
        """Check if construction approach is feasible"""

        # Check for extremely large projects
        area = requirements.dimensions.width * requirements.dimensions.length
        if area > 5000:  # ~70" x 70" blanket
            results["warnings"].append(
                f"Large project ({area:.0f} sq in) - consider breaking into panels "
                "or using lighter weight yarn"
            )

        # Check for very small projects
        if area < 50:  # Smaller than typical dishcloth
            results["warnings"].append(
                f"Small project ({area:.0f} sq in) - verify dimensions are correct"
            )

        # Check construction notes for conflicts
        notes = fabric_spec.construction_notes
        if (
            any("block" in note.lower() for note in notes)
            and fabric_spec.yarn_requirements.weight == "chunky"
        ):
            results["suggestions"].append(
                "Blocking may be less effective with chunky yarn - "
                "consider steam blocking or wet blocking techniques"
            )

        # Validate needle size recommendations
        gauge = fabric_spec.gauge["stitches_per_inch"]
        if gauge > 8:
            results["suggestions"].append(
                "Very tight gauge - ensure needle size recommendations allow for comfortable knitting"
            )
        elif gauge < 2:
            results["suggestions"].append(
                "Very loose gauge - pattern may lack structure, consider smaller needles"
            )

    def _validate_dimension_accuracy(
        self, requirements, actual_dimensions
    ) -> Dict[str, Any]:
        """Check if actual dimensions match target dimensions"""
        target_width = requirements.dimensions.width
        target_length = requirements.dimensions.length

        width_diff = abs(actual_dimensions["width"] - target_width)
        length_diff = abs(actual_dimensions["length"] - target_length)

        # Allow 0.5 inch tolerance
        tolerance = 0.5

        return {
            "width_accurate": width_diff <= tolerance,
            "length_accurate": length_diff <= tolerance,
            "width_difference": round(width_diff, 2),
            "length_difference": round(length_diff, 2),
            "within_tolerance": width_diff <= tolerance and length_diff <= tolerance,
        }
