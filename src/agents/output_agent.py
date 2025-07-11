from datetime import datetime
from typing import Any, Dict, List

from .base_agent import AgentType, BaseAgent, Message


class OutputAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.OUTPUT)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format and present the final pattern"""
        fabric_spec = input_data.get("fabric_spec")
        stitch_result = input_data.get("stitch_result")
        validation = input_data.get("validation", {})
        requirements = input_data.get("requirements")

        # Calculate estimated yardage
        estimated_yardage = self._calculate_yardage(requirements, fabric_spec)

        # Generate multiple output formats
        outputs = {
            "markdown": self._generate_markdown_pattern(
                fabric_spec, stitch_result, validation, requirements, estimated_yardage
            ),
            "text": self._generate_text_pattern(
                fabric_spec, stitch_result, validation, requirements, estimated_yardage
            ),
            "json": self._generate_json_pattern(
                fabric_spec, stitch_result, validation, requirements, estimated_yardage
            ),
            "summary": self._generate_summary(
                fabric_spec, stitch_result, validation, requirements, estimated_yardage
            ),
        }

        return {"outputs": outputs}

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return (
            "fabric_spec" in input_data
            and "construction_spec" in input_data
            and "stitch_result" in input_data
            and "requirements" in input_data
        )

    def handle_message(self, message: Message) -> Dict[str, Any]:
        return {"status": "acknowledged"}

    def _generate_markdown_pattern(
        self, fabric_spec, stitch_result, validation, requirements, estimated_yardage
    ) -> str:
        """Generate a markdown-formatted pattern"""

        title = self._generate_title(fabric_spec, requirements)

        md = f"""# {title}

## Pattern Information
- **Project Type**: {requirements.project_type.value.title()}
- **Finished Size**: {stitch_result["actual_dimensions"]["width"]}" wide × {stitch_result["actual_dimensions"]["length"]}" long
- **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Materials
- **Yarn**: {estimated_yardage} yards {fabric_spec.yarn_requirements.weight} weight {fabric_spec.yarn_requirements.fiber} yarn in {fabric_spec.yarn_requirements.color}
- **Needles**: {self._get_needle_size(fabric_spec.yarn_requirements.weight)}
- **Gauge**: {fabric_spec.gauge["stitches_per_inch"]} stitches and {fabric_spec.gauge["rows_per_inch"]} rows = 1 inch in {fabric_spec.stitch_pattern.name}

## Pattern Instructions

### Cast On
{stitch_result["stitch_instructions"][0]}

### Main Pattern: {fabric_spec.stitch_pattern.name}
"""

        # Add stitch pattern instructions
        for i, instruction in enumerate(fabric_spec.stitch_pattern.instructions, 1):
            md += f"{i}. {instruction}\n"

        md += f"\nRepeat rows 1-{fabric_spec.stitch_pattern.row_repeat} until piece measures desired length.\n"

        # Add border instructions if applicable
        if fabric_spec.border_pattern:
            md += f"\n### Border: {fabric_spec.border_pattern.name}\n"
            for i, instruction in enumerate(fabric_spec.border_pattern.instructions, 1):
                md += f"{i}. {instruction}\n"

        md += "\n### Finishing\nBind off all stitches loosely. Weave in ends. Block to measurements.\n"

        # Add construction notes
        if fabric_spec.construction_notes:
            md += "\n## Construction Notes\n"
            for note in fabric_spec.construction_notes:
                md += f"- {note}\n"

        # Add validation results if there are warnings or suggestions
        if validation and (validation.get("warnings") or validation.get("suggestions")):
            md += "\n## Pattern Notes\n"

            for warning in validation.get("warnings", []):
                md += f"⚠️ **Warning**: {warning}\n\n"

            for suggestion in validation.get("suggestions", []):
                md += f"💡 **Suggestion**: {suggestion}\n\n"

        return md

    def _generate_text_pattern(
        self, fabric_spec, stitch_result, validation, requirements, estimated_yardage
    ) -> str:
        """Generate a plain text pattern"""

        title = self._generate_title(fabric_spec, requirements)

        text = f"{title}\n{'=' * len(title)}\n\n"

        text += "MATERIALS:\n"
        text += f"Yarn: {estimated_yardage} yards {fabric_spec.yarn_requirements.weight} weight {fabric_spec.yarn_requirements.fiber}\n"
        text += (
            f"Needles: {self._get_needle_size(fabric_spec.yarn_requirements.weight)}\n"
        )
        text += f"Gauge: {fabric_spec.gauge['stitches_per_inch']} sts and {fabric_spec.gauge['rows_per_inch']} rows = 1 inch\n\n"

        text += "FINISHED SIZE:\n"
        text += f'{stitch_result["actual_dimensions"]["width"]}" wide x {stitch_result["actual_dimensions"]["length"]}" long\n\n'

        text += "INSTRUCTIONS:\n"
        for i, instruction in enumerate(stitch_result["stitch_instructions"], 1):
            text += f"{i}. {instruction}\n"

        if fabric_spec.construction_notes:
            text += "\nNOTES:\n"
            for note in fabric_spec.construction_notes:
                text += f"- {note}\n"

        return text

    def _generate_json_pattern(
        self, fabric_spec, stitch_result, validation, requirements, estimated_yardage
    ) -> Dict[str, Any]:
        """Generate a structured JSON pattern"""

        return {
            "pattern_info": {
                "title": self._generate_title(fabric_spec, requirements),
                "project_type": requirements.project_type.value,
                "generated_at": datetime.now().isoformat(),
            },
            "finished_size": {
                "width_inches": stitch_result["actual_dimensions"]["width"],
                "length_inches": stitch_result["actual_dimensions"]["length"],
            },
            "materials": {
                "yarn": {
                    "weight": fabric_spec.yarn_requirements.weight,
                    "fiber": fabric_spec.yarn_requirements.fiber,
                    "color": fabric_spec.yarn_requirements.color,
                    "estimated_yardage": estimated_yardage,
                },
                "needles": self._get_needle_size(fabric_spec.yarn_requirements.weight),
                "gauge": {
                    "stitches_per_inch": fabric_spec.gauge["stitches_per_inch"],
                    "rows_per_inch": fabric_spec.gauge["rows_per_inch"],
                },
            },
            "pattern_details": {
                "cast_on_stitches": stitch_result["cast_on_stitches"],
                "total_rows": stitch_result["total_rows"],
                "main_pattern": {
                    "name": fabric_spec.stitch_pattern.name,
                    "row_repeat": fabric_spec.stitch_pattern.row_repeat,
                    "stitch_repeat": fabric_spec.stitch_pattern.stitch_repeat,
                    "instructions": fabric_spec.stitch_pattern.instructions,
                },
                "border_pattern": {
                    "name": fabric_spec.border_pattern.name
                    if fabric_spec.border_pattern
                    else None,
                    "instructions": fabric_spec.border_pattern.instructions
                    if fabric_spec.border_pattern
                    else None,
                }
                if fabric_spec.border_pattern
                else None,
            },
            "instructions": stitch_result["stitch_instructions"],
            "construction_notes": fabric_spec.construction_notes,
            "validation": validation if validation else None,
        }

    def _generate_summary(
        self, fabric_spec, stitch_result, validation, requirements, estimated_yardage
    ) -> Dict[str, Any]:
        """Generate a concise pattern summary"""

        return {
            "title": self._generate_title(fabric_spec, requirements),
            "quick_stats": {
                "size": f'{stitch_result["actual_dimensions"]["width"]}" × {stitch_result["actual_dimensions"]["length"]}"',
                "yarn_needed": f"{estimated_yardage} yards {fabric_spec.yarn_requirements.weight} weight {fabric_spec.yarn_requirements.fiber}",
                "estimated_time": self._estimate_knitting_time(
                    stitch_result, fabric_spec
                ),
            },
            "key_techniques": self._identify_key_techniques(fabric_spec),
            "warnings_count": len(validation.get("warnings", [])) if validation else 0,
            "suggestions_count": len(validation.get("suggestions", []))
            if validation
            else 0,
            "is_valid": validation.get("is_valid", True) if validation else True,
        }

    def _generate_title(self, fabric_spec, requirements) -> str:
        """Generate a descriptive title for the pattern"""
        pattern_name = fabric_spec.stitch_pattern.name
        project_type = requirements.project_type.value.title()
        width = requirements.dimensions.width
        length = requirements.dimensions.length

        return f'{pattern_name} {project_type} ({width}" × {length}")'

    def _get_needle_size(self, yarn_weight: str) -> str:
        """Get recommended needle size for yarn weight"""
        needle_sizes = {
            "fingering": "US 3 (3.25mm)",
            "dk": "US 6 (4mm)",
            "worsted": "US 8 (5mm)",
            "chunky": "US 11 (8mm)",
        }
        return needle_sizes.get(yarn_weight, "US 8 (5mm)")

    def _estimate_knitting_time(self, stitch_result, fabric_spec) -> str:
        """Estimate knitting time based on pattern complexity"""
        total_stitches = stitch_result["cast_on_stitches"] * stitch_result["total_rows"]

        # Base stitches per hour (varies by pattern complexity)
        pattern_name = fabric_spec.stitch_pattern.name
        if pattern_name in ["Simple Cable", "Simple Lace"]:
            stitches_per_hour = 200  # Slower for pattern work
        else:
            stitches_per_hour = 400  # Faster for stockinette

        hours = total_stitches / stitches_per_hour

        if hours < 10:
            return f"{hours:.0f}-{hours * 1.5:.0f} hours"
        elif hours < 50:
            return f"{hours / 8:.0f}-{hours * 1.5 / 8:.0f} days"
        else:
            return f"{hours / 40:.0f}-{hours * 1.5 / 40:.0f} weeks"

    def _identify_key_techniques(self, fabric_spec) -> List[str]:
        """Identify key knitting techniques required"""
        techniques = ["cast on", "bind off"]

        pattern_name = fabric_spec.stitch_pattern.name
        if "Cable" in pattern_name:
            techniques.extend(["cables", "cable needle"])
        if "Lace" in pattern_name:
            techniques.extend(["yarn overs", "decreases"])
        if fabric_spec.border_pattern:
            techniques.append("stitch patterns")

        # Add basic stitches
        if pattern_name == "Stockinette":
            techniques.extend(["knit", "purl"])
        else:
            techniques.append("pattern reading")

        return techniques

    def _calculate_yardage(self, requirements, fabric_spec) -> int:
        """Calculate estimated yardage based on dimensions and yarn weight"""
        area = requirements.dimensions.width * requirements.dimensions.length
        yardage_per_sq_inch = {"worsted": 2.5, "dk": 3.0, "fingering": 4.0}
        yarn_weight = fabric_spec.yarn_requirements.weight
        estimated_yardage = int(area * yardage_per_sq_inch.get(yarn_weight, 2.5))

        # Add buffer for waste
        final_yardage = int(estimated_yardage * 1.2)
        return final_yardage
