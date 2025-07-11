from typing import Any, Dict

from ..agents.construction_agent import ConstructionAgent
from ..agents.fabric_agent import FabricAgent
from ..agents.output_agent import OutputAgent
from ..agents.requirements_agent import RequirementsAgent
from ..agents.stitch_agent import StitchAgent
from ..agents.validation_agent import ValidationAgent
from ..exceptions import WorkflowOrchestrationError


class PatternWorkflow:
    """Orchestrates the full pattern generation workflow"""

    def __init__(self):
        self.requirements_agent = RequirementsAgent()
        self.fabric_agent = FabricAgent()
        self.construction_agent = ConstructionAgent()
        self.stitch_agent = StitchAgent()
        self.validation_agent = ValidationAgent()
        self.output_agent = OutputAgent()

    def generate_pattern(self, user_request: str) -> Dict[str, Any]:
        """
        Generate a complete knitting pattern from user request

        Args:
            user_request: Natural language description of desired pattern

        Returns:
            Dictionary containing the complete pattern with all stages
        """
        try:
            # Validate user request
            if not user_request or not isinstance(user_request, str):
                raise WorkflowOrchestrationError(
                    "Invalid user request: must be a non-empty string",
                    failed_stage="input_validation",
                )

            # Stage 1: Parse user requirements
            try:
                requirements_input = {"user_request": user_request}
                requirements_result = self.requirements_agent.process(
                    requirements_input
                )
                requirements = requirements_result["requirements"]
            except Exception as e:
                raise WorkflowOrchestrationError(
                    f"Requirements processing failed: {str(e)}",
                    failed_stage="requirements",
                    agent_type="requirements",
                ) from e

            # Stage 2: Generate fabric specifications
            try:
                fabric_input = {"requirements": requirements}
                fabric_result = self.fabric_agent.process(fabric_input)
                fabric_spec = fabric_result["fabric_spec"]
            except Exception as e:
                raise WorkflowOrchestrationError(
                    f"Fabric specification failed: {str(e)}",
                    failed_stage="fabric",
                    agent_type="fabric",
                ) from e

            # Stage 3: Plan construction approach
            try:
                construction_input = {
                    "requirements": requirements,
                    "fabric_spec": fabric_spec,
                }
                construction_result = self.construction_agent.process(
                    construction_input
                )
                construction_spec = construction_result["construction_spec"]
            except Exception as e:
                raise WorkflowOrchestrationError(
                    f"Construction planning failed: {str(e)}",
                    failed_stage="construction",
                    agent_type="construction",
                ) from e

            # Stage 4: Generate stitch instructions and calculate stitch counts
            try:
                stitch_input = {
                    "fabric_spec": fabric_spec,
                    "construction_spec": construction_spec,
                }
                stitch_result = self.stitch_agent.process(stitch_input)
            except Exception as e:
                raise WorkflowOrchestrationError(
                    f"Stitch calculations failed: {str(e)}",
                    failed_stage="stitch",
                    agent_type="stitch",
                ) from e

            # Stage 5: Validate pattern accuracy and feasibility
            try:
                validation_input = {
                    "fabric_spec": fabric_spec,
                    "construction_spec": construction_spec,
                    "stitch_result": stitch_result,
                    "requirements": requirements,
                }
                validation_result = self.validation_agent.process(validation_input)
                validation = validation_result["validation"]
            except Exception as e:
                raise WorkflowOrchestrationError(
                    f"Pattern validation failed: {str(e)}",
                    failed_stage="validation",
                    agent_type="validation",
                ) from e

            # Stage 6: Generate formatted outputs
            try:
                output_input = {
                    "requirements": requirements,
                    "fabric_spec": fabric_spec,
                    "construction_spec": construction_spec,
                    "stitch_result": stitch_result,
                    "validation": validation,
                }
                output_result = self.output_agent.process(output_input)
                outputs = output_result["outputs"]
            except Exception as e:
                raise WorkflowOrchestrationError(
                    f"Output generation failed: {str(e)}",
                    failed_stage="output",
                    agent_type="output",
                ) from e

            # Compile complete pattern
            try:
                complete_pattern = {
                    "user_request": user_request,
                    "requirements": requirements,
                    "fabric_spec": fabric_spec,
                    "construction_spec": construction_spec,
                    "stitch_result": stitch_result,
                    "validation": validation,
                    "outputs": outputs,
                    "pattern_summary": self._create_pattern_summary(
                        requirements,
                        fabric_spec,
                        construction_spec,
                        stitch_result,
                        validation,
                    ),
                }

                return complete_pattern

            except Exception as e:
                raise WorkflowOrchestrationError(
                    f"Pattern compilation failed: {str(e)}",
                    failed_stage="pattern_compilation",
                ) from e

        except WorkflowOrchestrationError:
            raise
        except Exception as e:
            raise WorkflowOrchestrationError(
                f"Unexpected workflow error: {str(e)}", failed_stage="unknown"
            ) from e

    def _create_pattern_summary(
        self,
        requirements,
        fabric_spec,
        construction_spec,
        stitch_result,
        validation=None,
    ) -> Dict[str, Any]:
        """Create a human-readable pattern summary"""

        # Basic pattern info
        project_type = requirements.project_type.value.title()
        dimensions = requirements.dimensions

        # Material requirements
        yarn = fabric_spec.yarn_requirements

        # Calculate estimated yardage for summary
        estimated_yardage = self._calculate_yardage_for_summary(
            requirements, fabric_spec
        )

        # Stitch details
        cast_on = stitch_result["cast_on_stitches"]
        total_rows = stitch_result["total_rows"]
        actual_dims = stitch_result["actual_dimensions"]
        validation = stitch_result["dimension_validation"]

        # Create readable title
        pattern_name = fabric_spec.stitch_pattern.name
        title = f'{pattern_name} {project_type} ({actual_dims["width"]}" x {actual_dims["length"]}")'

        return {
            "title": title,
            "project_type": project_type,
            "finished_size": f'{actual_dims["width"]}" wide x {actual_dims["length"]}" long',
            "materials": {
                "yarn": f"{estimated_yardage} yards {yarn.weight} weight {yarn.fiber} yarn",
                "needles": self._get_needle_size(yarn.weight),
                "gauge": f"{fabric_spec.gauge['stitches_per_inch']} sts and {fabric_spec.gauge['rows_per_inch']} rows = 1 inch",
            },
            "cast_on_stitches": cast_on,
            "total_rows": total_rows,
            "main_pattern": fabric_spec.stitch_pattern.name,
            "border_pattern": fabric_spec.border_pattern.name
            if fabric_spec.border_pattern
            else None,
            "construction_notes": fabric_spec.construction_notes,
            "dimension_accuracy": {
                "target_size": f'{dimensions.width}" x {dimensions.length}"',
                "actual_size": f'{actual_dims["width"]}" x {actual_dims["length"]}"',
                "within_tolerance": validation["within_tolerance"],
                "differences": f'Width: ±{validation["width_difference"]}", Length: ±{validation["length_difference"]}"',
            },
            "validation_status": {
                "is_valid": validation.get("is_valid", True) if validation else True,
                "error_count": len(validation.get("errors", [])) if validation else 0,
                "warning_count": len(validation.get("warnings", []))
                if validation
                else 0,
                "suggestion_count": len(validation.get("suggestions", []))
                if validation
                else 0,
            }
            if validation
            else None,
        }

    def _get_needle_size(self, yarn_weight: str) -> str:
        """Get recommended needle size for yarn weight"""
        needle_sizes = {
            "fingering": "US 3 (3.25mm)",
            "dk": "US 6 (4mm)",
            "worsted": "US 8 (5mm)",
        }
        return needle_sizes.get(yarn_weight, "US 8 (5mm)")

    def _calculate_yardage_for_summary(self, requirements, fabric_spec) -> int:
        """Calculate estimated yardage for pattern summary"""
        area = requirements.dimensions.width * requirements.dimensions.length
        yardage_per_sq_inch = {"worsted": 2.5, "dk": 3.0, "fingering": 4.0}
        yarn_weight = fabric_spec.yarn_requirements.weight
        estimated_yardage = int(area * yardage_per_sq_inch.get(yarn_weight, 2.5))

        # Add buffer for waste
        final_yardage = int(estimated_yardage * 1.2)
        return final_yardage

    def validate_workflow(self) -> bool:
        """Validate that all agents are properly initialized"""
        return (
            self.requirements_agent is not None
            and self.fabric_agent is not None
            and self.construction_agent is not None
            and self.stitch_agent is not None
            and self.validation_agent is not None
            and self.output_agent is not None
        )
