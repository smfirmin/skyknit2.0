import json
from datetime import datetime

import pytest

from src.agents.base_agent import AgentType, Message
from src.agents.output_agent import OutputAgent
from src.models.knitting_models import (
    ConstructionSpec,
    Dimensions,
    FabricSpec,
    ProjectType,
    RequirementsSpec,
    StitchPattern,
    YarnSpec,
)


class TestOutputAgent:
    def setup_method(self):
        self.agent = OutputAgent()

        # Create common test data
        self.requirements = RequirementsSpec(
            project_type=ProjectType.BLANKET,
            dimensions=Dimensions(width=48.0, length=60.0),
            style_preferences={"texture": "simple"},
            special_requirements=[],
        )

        self.stitch_pattern = StitchPattern("Stockinette", 2, 1, ["Knit", "Purl"])
        self.border_pattern = StitchPattern(
            "Seed Stitch Border", 2, 2, ["K1, P1", "P1, K1"]
        )
        self.yarn = YarnSpec("worsted", "wool", "natural")

        self.fabric_spec = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=["simple construction", "work flat in rows"],
        )

        self.construction_spec = ConstructionSpec(
            target_dimensions=self.requirements.dimensions,
            construction_zones=[],
            construction_sequence=["cast_on", "main_body", "bind_off"],
            finishing_requirements=["weave_in_ends", "blocking"],
            structural_notes=["work flat"],
        )

        self.stitch_result = {
            "cast_on_stitches": 200,
            "total_rows": 330,
            "actual_dimensions": {"width": 50.0, "length": 60.0},
            "stitch_instructions": [
                "Cast on 200 stitches",
                "Begin Stockinette pattern:",
                "Row 1: Knit",
                "Row 2: Purl",
                "Repeat rows 1-2 until piece measures desired length",
                "Bind off all stitches loosely",
            ],
        }

        self.validation = {
            "is_valid": True,
            "errors": [],
            "warnings": ["This is a test warning"],
            "suggestions": ["This is a test suggestion"],
        }

    def test_initialization(self):
        assert self.agent.agent_type == AgentType.OUTPUT

    def test_validate_input_valid(self):
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": self.construction_spec,
            "stitch_result": self.stitch_result,
            "requirements": self.requirements,
        }
        assert self.agent.validate_input(input_data) is True

    def test_validate_input_missing_fields(self):
        # Missing fabric_spec
        input_data = {
            "construction_spec": self.construction_spec,
            "stitch_result": self.stitch_result,
            "requirements": self.requirements,
        }
        assert self.agent.validate_input(input_data) is False

    def test_process_complete(self):
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": self.construction_spec,
            "stitch_result": self.stitch_result,
            "requirements": self.requirements,
            "validation": self.validation,
        }
        result = self.agent.process(input_data)

        assert "outputs" in result
        outputs = result["outputs"]

        # Check all expected output formats
        assert "markdown" in outputs
        assert "text" in outputs
        assert "json" in outputs
        assert "summary" in outputs

        # Check that all outputs have content
        assert len(outputs["markdown"]) > 0
        assert len(outputs["text"]) > 0
        assert isinstance(outputs["json"], dict)
        assert isinstance(outputs["summary"], dict)

    def test_generate_title(self):
        title = self.agent._generate_title(self.fabric_spec, self.requirements)
        expected = 'Stockinette Blanket (48.0" × 60.0")'
        assert title == expected

    def test_get_needle_size(self):
        assert self.agent._get_needle_size("worsted") == "US 8 (5mm)"
        assert self.agent._get_needle_size("dk") == "US 6 (4mm)"
        assert self.agent._get_needle_size("fingering") == "US 3 (3.25mm)"
        assert self.agent._get_needle_size("chunky") == "US 11 (8mm)"
        assert self.agent._get_needle_size("unknown") == "US 8 (5mm)"  # Default

    def test_calculate_yardage_worsted(self):
        yardage = self.agent._calculate_yardage(self.requirements, self.fabric_spec)

        # 48" × 60" = 2880 sq in
        # Worsted: 2.5 yards per sq in
        # With 20% buffer: 2880 * 2.5 * 1.2 = 8640
        expected = int(2880 * 2.5 * 1.2)
        assert yardage == expected

    def test_calculate_yardage_dk(self):
        dk_yarn = YarnSpec("dk", "wool", "natural")
        dk_fabric = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=dk_yarn,
            gauge={"stitches_per_inch": 5.0, "rows_per_inch": 6.0},
            construction_notes=[],
        )

        yardage = self.agent._calculate_yardage(self.requirements, dk_fabric)

        # 2880 sq in * 3.0 yards/sq in * 1.2 buffer = 10368
        expected = int(2880 * 3.0 * 1.2)
        assert yardage == expected

    def test_calculate_yardage_unknown_weight(self):
        unknown_yarn = YarnSpec("unknown_weight", "wool", "natural")
        unknown_fabric = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=unknown_yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=[],
        )

        yardage = self.agent._calculate_yardage(self.requirements, unknown_fabric)

        # Should default to worsted calculation (2.5 yards/sq in)
        expected = int(2880 * 2.5 * 1.2)
        assert yardage == expected

    def test_estimate_knitting_time_stockinette(self):
        time_estimate = self.agent._estimate_knitting_time(
            self.stitch_result, self.fabric_spec
        )

        # 200 * 330 = 66000 stitches
        # Stockinette: 400 stitches/hour = 165 hours
        # Should be in weeks range
        assert "week" in time_estimate.lower()

    def test_estimate_knitting_time_cable(self):
        cable_pattern = StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"])
        cable_fabric = FabricSpec(
            stitch_pattern=cable_pattern,
            border_pattern=self.border_pattern,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=[],
        )

        time_estimate = self.agent._estimate_knitting_time(
            self.stitch_result, cable_fabric
        )

        # Cable patterns are slower (200 stitches/hour vs 400)
        # Should take longer than stockinette
        assert isinstance(time_estimate, str)
        assert len(time_estimate) > 0

    def test_estimate_knitting_time_quick_project(self):
        quick_stitch_result = {
            "cast_on_stitches": 50,
            "total_rows": 60,
            "actual_dimensions": {"width": 12.5, "length": 10.9},
            "stitch_instructions": [],
        }

        time_estimate = self.agent._estimate_knitting_time(
            quick_stitch_result, self.fabric_spec
        )

        # 50 * 60 = 3000 stitches / 400 = 7.5 hours
        # Should be in hours range
        assert "hour" in time_estimate.lower()

    def test_identify_key_techniques_stockinette(self):
        techniques = self.agent._identify_key_techniques(self.fabric_spec)

        assert "cast on" in techniques
        assert "bind off" in techniques
        assert "knit" in techniques
        assert "purl" in techniques
        assert "stitch patterns" in techniques  # Due to border

    def test_identify_key_techniques_cable(self):
        cable_pattern = StitchPattern("Simple Cable", 8, 12, ["C6F", "K6"])
        cable_fabric = FabricSpec(
            stitch_pattern=cable_pattern,
            border_pattern=None,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 6.0},
            construction_notes=[],
        )

        techniques = self.agent._identify_key_techniques(cable_fabric)

        assert "cables" in techniques
        assert "cable needle" in techniques
        assert "pattern reading" in techniques

    def test_identify_key_techniques_lace(self):
        lace_pattern = StitchPattern("Simple Lace", 4, 8, ["YO", "K2tog"])
        lace_fabric = FabricSpec(
            stitch_pattern=lace_pattern,
            border_pattern=None,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 3.5, "rows_per_inch": 5.0},
            construction_notes=[],
        )

        techniques = self.agent._identify_key_techniques(lace_fabric)

        assert "yarn overs" in techniques
        assert "decreases" in techniques
        assert "pattern reading" in techniques

    def test_generate_markdown_pattern(self):
        estimated_yardage = 8640
        markdown = self.agent._generate_markdown_pattern(
            self.fabric_spec,
            self.stitch_result,
            self.validation,
            self.requirements,
            estimated_yardage,
        )

        # Check structure and content
        assert "# Stockinette Blanket" in markdown
        assert "## Pattern Information" in markdown
        assert "## Materials" in markdown
        assert "## Pattern Instructions" in markdown
        assert "8640 yards" in markdown
        assert "US 8 (5mm)" in markdown
        assert "⚠️ **Warning**: This is a test warning" in markdown
        assert "💡 **Suggestion**: This is a test suggestion" in markdown

    def test_generate_markdown_pattern_no_validation(self):
        estimated_yardage = 8640
        markdown = self.agent._generate_markdown_pattern(
            self.fabric_spec,
            self.stitch_result,
            {},
            self.requirements,
            estimated_yardage,
        )

        # Should not have warning/suggestion sections
        assert "⚠️" not in markdown
        assert "💡" not in markdown

    def test_generate_text_pattern(self):
        estimated_yardage = 8640
        text = self.agent._generate_text_pattern(
            self.fabric_spec,
            self.stitch_result,
            self.validation,
            self.requirements,
            estimated_yardage,
        )

        # Check structure and content
        assert "Stockinette Blanket" in text
        assert "MATERIALS:" in text
        assert "FINISHED SIZE:" in text
        assert "INSTRUCTIONS:" in text
        assert "NOTES:" in text
        assert "8640 yards" in text
        assert '50.0" wide x 60.0" long' in text

    def test_generate_json_pattern(self):
        estimated_yardage = 8640
        json_pattern = self.agent._generate_json_pattern(
            self.fabric_spec,
            self.stitch_result,
            self.validation,
            self.requirements,
            estimated_yardage,
        )

        # Check structure
        assert "pattern_info" in json_pattern
        assert "finished_size" in json_pattern
        assert "materials" in json_pattern
        assert "pattern_details" in json_pattern
        assert "instructions" in json_pattern
        assert "construction_notes" in json_pattern
        assert "validation" in json_pattern

        # Check content
        assert (
            json_pattern["pattern_info"]["title"]
            == 'Stockinette Blanket (48.0" × 60.0")'
        )
        assert json_pattern["materials"]["yarn"]["estimated_yardage"] == 8640
        assert json_pattern["pattern_details"]["cast_on_stitches"] == 200
        assert json_pattern["validation"] == self.validation

    def test_generate_json_pattern_no_border(self):
        fabric_no_border = FabricSpec(
            stitch_pattern=self.stitch_pattern,
            border_pattern=None,
            yarn_requirements=self.yarn,
            gauge={"stitches_per_inch": 4.0, "rows_per_inch": 5.5},
            construction_notes=[],
        )

        estimated_yardage = 8640
        json_pattern = self.agent._generate_json_pattern(
            fabric_no_border,
            self.stitch_result,
            self.validation,
            self.requirements,
            estimated_yardage,
        )

        # Border pattern should be None
        assert json_pattern["pattern_details"]["border_pattern"] is None

    def test_generate_summary(self):
        estimated_yardage = 8640
        summary = self.agent._generate_summary(
            self.fabric_spec,
            self.stitch_result,
            self.validation,
            self.requirements,
            estimated_yardage,
        )

        # Check structure
        assert "title" in summary
        assert "quick_stats" in summary
        assert "key_techniques" in summary
        assert "warnings_count" in summary
        assert "suggestions_count" in summary
        assert "is_valid" in summary

        # Check content
        assert summary["title"] == 'Stockinette Blanket (48.0" × 60.0")'
        assert summary["warnings_count"] == 1
        assert summary["suggestions_count"] == 1
        assert summary["is_valid"] is True

        # Check quick stats
        quick_stats = summary["quick_stats"]
        assert '50.0" × 60.0"' in quick_stats["size"]
        assert "8640 yards" in quick_stats["yarn_needed"]
        assert isinstance(quick_stats["estimated_time"], str)

    def test_generate_summary_no_validation(self):
        estimated_yardage = 8640
        summary = self.agent._generate_summary(
            self.fabric_spec,
            self.stitch_result,
            None,
            self.requirements,
            estimated_yardage,
        )

        # Should handle None validation gracefully
        assert summary["warnings_count"] == 0
        assert summary["suggestions_count"] == 0
        assert summary["is_valid"] is True

    def test_handle_message(self):
        message = Message(
            sender=AgentType.VALIDATION,
            recipient=AgentType.OUTPUT,
            content={"test": "data"},
            message_type="test",
        )
        result = self.agent.handle_message(message)
        assert result["status"] == "acknowledged"

    def test_process_without_validation(self):
        input_data = {
            "fabric_spec": self.fabric_spec,
            "construction_spec": self.construction_spec,
            "stitch_result": self.stitch_result,
            "requirements": self.requirements,
            # No validation key
        }
        result = self.agent.process(input_data)

        # Should work without validation
        assert "outputs" in result
        outputs = result["outputs"]
        assert all(key in outputs for key in ["markdown", "text", "json", "summary"])

    def test_markdown_pattern_includes_all_instructions(self):
        estimated_yardage = 8640
        markdown = self.agent._generate_markdown_pattern(
            self.fabric_spec,
            self.stitch_result,
            {},
            self.requirements,
            estimated_yardage,
        )

        # Should include stitch pattern instructions
        assert "1. Knit" in markdown
        assert "2. Purl" in markdown
        assert "Repeat rows 1-2" in markdown

        # Should include border instructions
        assert "### Border: Seed Stitch Border" in markdown
        assert "K1, P1" in markdown or "P1, K1" in markdown

    def test_json_pattern_serializable(self):
        estimated_yardage = 8640
        json_pattern = self.agent._generate_json_pattern(
            self.fabric_spec,
            self.stitch_result,
            self.validation,
            self.requirements,
            estimated_yardage,
        )

        # Should be serializable to JSON string
        json_string = json.dumps(json_pattern)
        assert isinstance(json_string, str)
        assert len(json_string) > 0

        # Should be deserializable
        parsed = json.loads(json_string)
        assert parsed == json_pattern
