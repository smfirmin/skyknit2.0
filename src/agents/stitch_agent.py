from typing import Any, Dict, List

from ..exceptions import DimensionError, StitchCalculationError, ValidationError
from .base_agent import AgentType, BaseAgent, Message


class StitchAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.STITCH)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate stitch calculations and detailed instructions from construction plan"""
        try:
            # Validate input first
            if not self.validate_input(input_data):
                raise ValidationError(
                    "Invalid input data for stitch processing",
                    field="fabric_spec or construction_spec",
                    expected="FabricSpec and ConstructionSpec objects",
                    value=f"fabric_spec={type(input_data.get('fabric_spec'))}, construction_spec={type(input_data.get('construction_spec'))}",
                )

            fabric_spec = input_data.get("fabric_spec")
            construction_spec = input_data.get("construction_spec")

            # Validate gauge and dimensions before calculations
            self._validate_calculation_inputs(fabric_spec, construction_spec)

            # Calculate exact stitch counts using construction plan + gauge
            cast_on_stitches = self._calculate_cast_on_stitches(
                fabric_spec, construction_spec
            )
            total_rows = self._calculate_total_rows(fabric_spec, construction_spec)

            # Generate stitch-by-stitch instructions from construction plan
            stitch_instructions = self._generate_stitch_instructions(
                construction_spec, fabric_spec, cast_on_stitches
            )

            # Calculate actual dimensions for reference
            actual_dimensions = self._calculate_actual_dimensions(
                fabric_spec, cast_on_stitches, total_rows
            )

            # Validate that calculated dimensions are reasonable
            self._validate_calculated_dimensions(
                construction_spec.target_dimensions, actual_dimensions
            )

            return {
                "stitch_instructions": stitch_instructions,
                "cast_on_stitches": cast_on_stitches,
                "total_rows": total_rows,
                "actual_dimensions": actual_dimensions,
                "dimension_validation": self._validate_dimensions_against_target(
                    construction_spec.target_dimensions, actual_dimensions
                ),
            }

        except (ValidationError, StitchCalculationError, DimensionError):
            raise
        except Exception as e:
            raise StitchCalculationError(
                f"Unexpected error during stitch calculations: {str(e)}"
            ) from e

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data for stitch processing"""
        if not isinstance(input_data, dict):
            return False

        if "fabric_spec" not in input_data or "construction_spec" not in input_data:
            return False

        fabric_spec = input_data["fabric_spec"]
        construction_spec = input_data["construction_spec"]

        return (
            hasattr(fabric_spec, "gauge")
            and hasattr(fabric_spec, "stitch_pattern")
            and hasattr(construction_spec, "target_dimensions")
            and hasattr(construction_spec, "construction_zones")
        )

    def handle_message(self, message: Message) -> Dict[str, Any]:
        return {"status": "acknowledged"}

    def _calculate_cast_on_stitches(self, fabric_spec, construction_spec) -> int:
        """Calculate exact number of stitches needed using construction zones"""
        try:
            target_width = construction_spec.target_dimensions.width
            stitches_per_inch = fabric_spec.gauge["stitches_per_inch"]

            # Base calculation for target width (main pattern area)
            base_stitches = int(target_width * stitches_per_inch)

            if base_stitches <= 0:
                raise StitchCalculationError(
                    f"Invalid base stitch calculation: {base_stitches} (width={target_width}, gauge={stitches_per_inch})",
                    calculation_type="cast_on_stitches",
                )

            # Find main body zone and border zones
            main_zone = next(
                (
                    z
                    for z in construction_spec.construction_zones
                    if z.name == "main_body"
                ),
                None,
            )
            border_zones = [
                z for z in construction_spec.construction_zones if z.name == "border"
            ]

            # Adjust main pattern for stitch repeat if needed
            pattern_stitches = base_stitches
            if main_zone and main_zone.stitch_pattern.stitch_repeat > 1:
                stitch_repeat = main_zone.stitch_pattern.stitch_repeat
                if stitch_repeat <= 0:
                    raise StitchCalculationError(
                        f"Invalid stitch repeat: {stitch_repeat}",
                        calculation_type="pattern_repeat",
                    )
                # Round to nearest multiple of stitch repeat
                pattern_stitches = (
                    (pattern_stitches + stitch_repeat - 1) // stitch_repeat
                ) * stitch_repeat

            # Add border stitches on top of the main pattern
            border_stitches = 0
            if border_zones:
                border_stitches = 8  # 4 stitches each side for seed stitch border

            total_stitches = pattern_stitches + border_stitches

            if total_stitches <= 0:
                raise StitchCalculationError(
                    f"Invalid total stitch count: {total_stitches}",
                    calculation_type="cast_on_stitches",
                )

            return total_stitches

        except StitchCalculationError:
            raise
        except Exception as e:
            raise StitchCalculationError(
                f"Failed to calculate cast-on stitches: {str(e)}",
                calculation_type="cast_on_stitches",
            ) from e

    def _calculate_total_rows(self, fabric_spec, construction_spec) -> int:
        """Calculate exact number of rows needed using construction plan"""
        try:
            target_length = construction_spec.target_dimensions.length
            rows_per_inch = fabric_spec.gauge["rows_per_inch"]

            base_rows = int(target_length * rows_per_inch)

            if base_rows <= 0:
                raise StitchCalculationError(
                    f"Invalid base row calculation: {base_rows} (length={target_length}, gauge={rows_per_inch})",
                    calculation_type="total_rows",
                )

            # Find main body zone for row repeat adjustment
            main_zone = next(
                (
                    z
                    for z in construction_spec.construction_zones
                    if z.name == "main_body"
                ),
                None,
            )

            # Adjust for row repeat to end on complete pattern
            if main_zone and main_zone.stitch_pattern.row_repeat > 1:
                row_repeat = main_zone.stitch_pattern.row_repeat
                if row_repeat <= 0:
                    raise StitchCalculationError(
                        f"Invalid row repeat: {row_repeat}",
                        calculation_type="pattern_repeat",
                    )
                base_rows = ((base_rows + row_repeat - 1) // row_repeat) * row_repeat

            if base_rows <= 0:
                raise StitchCalculationError(
                    f"Invalid final row count: {base_rows}",
                    calculation_type="total_rows",
                )

            return base_rows

        except StitchCalculationError:
            raise
        except Exception as e:
            raise StitchCalculationError(
                f"Failed to calculate total rows: {str(e)}",
                calculation_type="total_rows",
            ) from e

    def _generate_stitch_instructions(
        self, construction_spec, fabric_spec, cast_on_stitches
    ) -> List[str]:
        """Generate detailed stitch-by-stitch instructions from construction plan"""
        instructions = []

        # Cast on instruction
        instructions.append(f"Cast on {cast_on_stitches} stitches")

        # Follow construction sequence
        for step in construction_spec.construction_sequence:
            if step == "cast_on":
                continue  # Already handled
            elif step == "bottom_border":
                border_zone = next(
                    (
                        z
                        for z in construction_spec.construction_zones
                        if z.name == "border"
                    ),
                    None,
                )
                if border_zone:
                    border_instructions = self._generate_border_instructions(
                        border_zone.stitch_pattern
                    )
                    instructions.extend(border_instructions)
            elif step == "main_body_with_side_borders" or step == "main_body":
                main_zone = next(
                    (
                        z
                        for z in construction_spec.construction_zones
                        if z.name == "main_body"
                    ),
                    None,
                )
                if main_zone:
                    main_instructions = self._generate_main_pattern_instructions(
                        main_zone.stitch_pattern
                    )
                    instructions.extend(main_instructions)
            elif step == "top_border":
                instructions.append("Repeat border pattern as at beginning")
            elif step == "bind_off":
                instructions.append("Bind off all stitches loosely")
            elif step == "finishing":
                instructions.extend(
                    self._generate_finishing_instructions(
                        construction_spec.finishing_requirements
                    )
                )

        return instructions

    def _generate_border_instructions(self, border_pattern) -> List[str]:
        """Generate border pattern instructions"""
        instructions = []
        for i, instruction in enumerate(border_pattern.instructions, 1):
            instructions.append(f"Border Row {i}: {instruction}")
        instructions.append(
            f"Repeat border rows 1-{border_pattern.row_repeat} for {border_pattern.row_repeat} total rows"
        )
        return instructions

    def _generate_main_pattern_instructions(self, stitch_pattern) -> List[str]:
        """Generate main stitch pattern instructions"""
        instructions = []

        # Add pattern setup
        instructions.append(f"Begin {stitch_pattern.name} pattern:")

        # Add each row of the pattern
        for i, instruction in enumerate(stitch_pattern.instructions, 1):
            instructions.append(f"Row {i}: {instruction}")

        # Add repeat instruction
        instructions.append(
            f"Repeat rows 1-{stitch_pattern.row_repeat} until piece measures desired length"
        )

        return instructions

    def _calculate_actual_dimensions(
        self, fabric_spec, cast_on_stitches, total_rows
    ) -> Dict[str, float]:
        """Calculate actual dimensions based on stitch counts and gauge"""
        actual_width = cast_on_stitches / fabric_spec.gauge["stitches_per_inch"]
        actual_length = total_rows / fabric_spec.gauge["rows_per_inch"]

        return {"width": round(actual_width, 2), "length": round(actual_length, 2)}

    def _generate_finishing_instructions(self, finishing_requirements) -> List[str]:
        """Generate finishing instructions from construction plan"""
        instructions = []

        for requirement in finishing_requirements:
            if requirement == "weave_in_ends":
                instructions.append("Weave in all loose ends securely")
            elif requirement == "blocking":
                instructions.append(
                    "Block piece to measurements, allowing to dry completely"
                )
            elif requirement == "cable_blocking":
                instructions.append("Block gently to maintain cable definition")
            elif requirement == "aggressive_blocking":
                instructions.append("Block aggressively to open up lace pattern")

        return instructions

    def _validate_calculation_inputs(self, fabric_spec, construction_spec) -> None:
        """Validate inputs before performing calculations"""
        # Validate gauge
        gauge = fabric_spec.gauge
        if "stitches_per_inch" not in gauge or "rows_per_inch" not in gauge:
            raise StitchCalculationError(
                f"Invalid gauge specification: {gauge}",
                calculation_type="gauge_validation",
            )

        stitches_per_inch = gauge["stitches_per_inch"]
        rows_per_inch = gauge["rows_per_inch"]

        if stitches_per_inch <= 0 or rows_per_inch <= 0:
            raise StitchCalculationError(
                f"Invalid gauge values: {stitches_per_inch} stitches/inch, {rows_per_inch} rows/inch",
                calculation_type="gauge_validation",
            )

        # Validate target dimensions
        target_dims = construction_spec.target_dimensions
        if target_dims.width <= 0 or target_dims.length <= 0:
            raise DimensionError(
                f'Invalid target dimensions: {target_dims.width}" x {target_dims.length}"',
                target_dimensions={
                    "width": target_dims.width,
                    "length": target_dims.length,
                },
            )

        # Validate construction zones exist
        if not construction_spec.construction_zones:
            raise StitchCalculationError(
                "No construction zones defined",
                calculation_type="construction_validation",
            )

    def _validate_calculated_dimensions(
        self, target_dimensions, actual_dimensions
    ) -> None:
        """Validate that calculated dimensions are reasonable"""
        actual_width = actual_dimensions["width"]
        actual_length = actual_dimensions["length"]

        # Check for impossible dimensions
        if actual_width <= 0 or actual_length <= 0:
            raise DimensionError(
                f'Calculated invalid dimensions: {actual_width}" x {actual_length}"',
                target_dimensions={
                    "width": target_dimensions.width,
                    "length": target_dimensions.length,
                },
                actual_dimensions=actual_dimensions,
            )

        # Check for extremely large dimensions (likely calculation error)
        if actual_width > 1000 or actual_length > 1000:
            raise DimensionError(
                f'Calculated dimensions too large: {actual_width}" x {actual_length}". Likely calculation error.',
                target_dimensions={
                    "width": target_dimensions.width,
                    "length": target_dimensions.length,
                },
                actual_dimensions=actual_dimensions,
            )

    def _validate_dimensions_against_target(
        self, target_dimensions, actual_dimensions
    ) -> Dict[str, Any]:
        """Validate calculated dimensions against target with tolerance"""
        target_width = target_dimensions.width
        target_length = target_dimensions.length
        actual_width = actual_dimensions["width"]
        actual_length = actual_dimensions["length"]

        # Calculate differences
        width_diff = abs(actual_width - target_width)
        length_diff = abs(actual_length - target_length)

        # Set tolerance (0.5 inches)
        tolerance = 0.5

        width_accurate = width_diff <= tolerance
        length_accurate = length_diff <= tolerance
        within_tolerance = width_accurate and length_accurate

        return {
            "width_accurate": width_accurate,
            "length_accurate": length_accurate,
            "within_tolerance": within_tolerance,
            "width_difference": round(width_diff, 2),
            "length_difference": round(length_diff, 2),
            "tolerance": tolerance,
        }
