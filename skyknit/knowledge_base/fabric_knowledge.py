"""
Fabric Knowledge Base - Unstructured rules and principles for fabric behavior.

This module contains the knowledge that LLMs will use to reason about
how different yarn and pattern combinations will behave to create fabric.
"""

from dataclasses import dataclass

from .schemas import YarnWeight


@dataclass
class FabricRule:
    """A rule about fabric behavior"""

    condition: str  # When this rule applies
    effect: str  # What happens
    confidence: float  # How confident we are (0.0 to 1.0)
    source: str  # Where this knowledge comes from


class FabricKnowledgeBase:
    """
    Unstructured knowledge base for fabric behavior and yarn-pattern interactions.

    This contains rules and principles that LLMs can use to reason about
    fabric properties without needing pre-computed combinations.
    """

    def __init__(self):
        self.rules = self._load_fabric_rules()
        self.gauge_principles = self._load_gauge_principles()
        self.drape_principles = self._load_drape_principles()
        self.warmth_principles = self._load_warmth_principles()
        self.construction_principles = self._load_construction_principles()

    def _load_fabric_rules(self) -> list[FabricRule]:
        """Load general fabric behavior rules"""
        return [
            FabricRule(
                condition="Pattern has high stitch density (cables, textured stitches)",
                effect="Fabric will be less stretchy and more structured",
                confidence=0.9,
                source="General knitting knowledge",
            ),
            FabricRule(
                condition="Pattern creates ribbing (alternating knit/purl columns)",
                effect="Fabric will have horizontal stretch and recovery",
                confidence=0.95,
                source="Fundamental knitting properties",
            ),
            FabricRule(
                condition="Stockinette stitch with any yarn",
                effect="Fabric will curl at edges due to stitch structure",
                confidence=0.98,
                source="Fundamental knitting properties",
            ),
            FabricRule(
                condition="Pattern alternates knit/purl frequently (seed stitch, moss stitch)",
                effect="Fabric will lie flat and not curl",
                confidence=0.95,
                source="Fundamental knitting properties",
            ),
            FabricRule(
                condition="Garter stitch (knit every row)",
                effect="Fabric will be very stretchy vertically, somewhat horizontally",
                confidence=0.92,
                source="Fundamental knitting properties",
            ),
            FabricRule(
                condition="Complex cable patterns",
                effect="Fabric will draw in width due to cable crossings",
                confidence=0.85,
                source="Cable knitting experience",
            ),
            FabricRule(
                condition="Lace patterns with yarn overs",
                effect="Fabric will be more open and drapey",
                confidence=0.88,
                source="Lace knitting experience",
            ),
        ]

    def _load_gauge_principles(self) -> dict[str, str]:
        """Load principles about how gauge affects fabric"""
        return {
            "tight_gauge": """
            Tighter gauge (more stitches per inch) creates:
            - Firmer, more structured fabric
            - Better stitch definition
            - Less drape, more stability
            - Warmer fabric due to less air space
            - More yarn usage
            Best for: structured garments, cables, colorwork
            """,
            "loose_gauge": """
            Looser gauge (fewer stitches per inch) creates:
            - Softer, more drapey fabric
            - More stretch and give
            - Better drape for flowing garments
            - Cooler fabric due to more air space
            - Less yarn usage
            Best for: flowing garments, summer knits, quick projects
            """,
            "gauge_yarn_weight_relationship": """
            Yarn weight affects natural gauge:
            - Fingering (1): 28-32 stitches per 4 inches
            - Sport (2): 24-26 stitches per 4 inches
            - DK (3): 22-24 stitches per 4 inches
            - Worsted (4): 18-20 stitches per 4 inches
            - Bulky (5): 12-15 stitches per 4 inches
            - Super Bulky (6): 8-11 stitches per 4 inches

            Going significantly off these ranges changes fabric behavior.
            """,
            "pattern_gauge_interaction": """
            Different patterns affect gauge:
            - Stockinette: baseline gauge
            - Ribbing: draws in width by 10-30%
            - Seed stitch: slightly tighter gauge
            - Cables: significantly tighter gauge, draws in width
            - Lace: looser gauge, more open
            - Garter: shorter and wider than stockinette
            """,
        }

    def _load_drape_principles(self) -> dict[str, str]:
        """Load principles about fabric drape"""
        return {
            "fiber_drape": """
            Fiber content affects drape:
            - Wool: moderate drape, good structure
            - Cotton: crisp, less drape than wool
            - Silk: excellent drape, flows beautifully
            - Alpaca: very drapey, can be too soft for structure
            - Acrylic: varies widely, often less drape than natural fibers
            - Bamboo: excellent drape, silk-like
            - Linen: crisp when new, softens with wear
            """,
            "yarn_weight_drape": """
            Yarn weight affects drape:
            - Fingering: excellent drape, fluid movement
            - Sport: good drape, still structured
            - DK: moderate drape, balanced
            - Worsted: less drape, more structure
            - Bulky: minimal drape, very structured
            - Super Bulky: stiff, sculptural
            """,
            "pattern_drape": """
            Pattern affects drape:
            - Stockinette: natural drape of the yarn
            - Ribbing: structured, less drape
            - Seed stitch: structured, minimal drape
            - Cables: very structured, minimal drape
            - Lace: enhanced drape, flows beautifully
            - Garter: bouncy, moderate drape
            """,
            "drape_combinations": """
            Drape is multiplicative:
            - Drapey yarn + drapey pattern = very fluid fabric
            - Structured yarn + structured pattern = very firm fabric
            - Drapey yarn + structured pattern = balanced fabric
            - Structured yarn + drapey pattern = moderate drape
            """,
        }

    def _load_warmth_principles(self) -> dict[str, str]:
        """Load principles about fabric warmth"""
        return {
            "fiber_warmth": """
            Fiber warmth properties:
            - Wool: excellent insulation, warm even when damp
            - Alpaca: very warm, hollow fibers trap air
            - Cashmere: extremely warm for its weight
            - Cotton: cool, not insulating
            - Linen: very cool, wicks moisture
            - Silk: moderate warmth, good temperature regulation
            - Acrylic: moderate warmth, depends on construction
            - Bamboo: cool, moisture-wicking
            """,
            "gauge_warmth": """
            Gauge affects warmth:
            - Tight gauge: warmer, less air circulation
            - Loose gauge: cooler, more air circulation
            - Very loose gauge: can be drafty
            """,
            "pattern_warmth": """
            Pattern affects warmth:
            - Stockinette: moderate warmth
            - Ribbing: warmer due to thickness
            - Seed stitch: warmer due to texture
            - Cables: very warm due to thickness
            - Lace: cooler due to openness
            - Garter: warm due to thickness
            """,
            "layering_warmth": """
            Fabric thickness affects warmth:
            - Thin fabrics: good for layering
            - Medium fabrics: versatile for most climates
            - Thick fabrics: very warm, good for outerwear
            """,
        }

    def _load_construction_principles(self) -> dict[str, str]:
        """Load principles about construction considerations"""
        return {
            "yarn_splitting": """
            Yarn splitting during construction:
            - Tightly plied yarns: minimal splitting
            - Loosely plied yarns: more splitting
            - Single-ply yarns: significant splitting
            - Fuzzy yarns (mohair, alpaca): can split easily
            - Smooth yarns (cotton, silk): minimal splitting

            Splitting affects stitch definition and ease of construction.
            """,
            "stitch_definition": """
            Stitch definition factors:
            - Smooth yarns: excellent definition
            - Fuzzy yarns: poor definition, soft look
            - Dark colors: hide stitch definition
            - Light colors: show stitch definition clearly
            - Tight gauge: better definition
            - Loose gauge: softer definition
            """,
            "edge_behavior": """
            Edge behavior by pattern:
            - Stockinette: curls significantly, needs border
            - Ribbing: lies flat, good for edges
            - Seed stitch: lies flat, excellent for borders
            - Garter: lies flat, traditional border
            - Cables: may need border depending on pattern
            - Lace: usually lies flat after blocking
            """,
            "blocking_behavior": """
            Blocking affects different fibers differently:
            - Wool: blocks well, holds shape
            - Cotton: blocks moderately, may relax
            - Silk: blocks beautifully, stays blocked
            - Acrylic: minimal blocking effect
            - Alpaca: blocks well but may grow
            - Linen: blocks well, gets softer
            """,
            "durability_factors": """
            Durability considerations:
            - Wool: durable, self-cleaning
            - Cotton: very durable, machine washable
            - Silk: delicate, needs care
            - Acrylic: very durable, easy care
            - Alpaca: moderately durable, pills easily
            - Linen: extremely durable, improves with age

            Pattern affects durability:
            - Simple patterns: more durable
            - Complex patterns: may snag or lose definition
            - Textured patterns: hide wear better
            """,
        }

    def get_fabric_prediction(
        self, pattern_category: str, yarn_weight: YarnWeight, fiber_type: str
    ) -> dict[str, str]:
        """
        Predict fabric behavior based on pattern and yarn combination.

        This method demonstrates how an LLM might reason about fabric properties
        using the knowledge base principles.
        """
        prediction = {
            "gauge_impact": "",
            "drape_quality": "",
            "warmth_level": "",
            "recommendations": [],
        }

        # Gauge prediction
        if yarn_weight == YarnWeight.FINGERING:
            prediction["gauge_impact"] = "Fine gauge, excellent stitch definition"
        elif yarn_weight == YarnWeight.WORSTED:
            prediction["gauge_impact"] = (
                "Standard gauge, good balance of speed and definition"
            )
        elif yarn_weight in [YarnWeight.BULKY, YarnWeight.SUPER_BULKY]:
            prediction["gauge_impact"] = "Quick to knit, less detail definition"

        # Drape prediction
        if pattern_category == "lace":
            prediction["drape_quality"] = "Excellent drape, flows beautifully"
        elif pattern_category == "cable":
            prediction["drape_quality"] = "Structured, minimal drape"
        elif pattern_category == "basic":
            prediction["drape_quality"] = "Natural drape of the yarn"

        # Warmth prediction
        warmth_factors = []
        if fiber_type == "natural" and "wool" in fiber_type.lower():
            warmth_factors.append("wool insulation")
        if pattern_category in ["cable", "textured"]:
            warmth_factors.append("textured thickness")
        if yarn_weight in [YarnWeight.WORSTED, YarnWeight.BULKY]:
            warmth_factors.append("substantial yarn weight")

        prediction["warmth_level"] = f"Moderate to warm ({', '.join(warmth_factors)})"

        return prediction

    def get_compatibility_score(
        self, pattern_category: str, yarn_weight: YarnWeight, fiber_type: str
    ) -> float:
        """
        Calculate compatibility score between pattern and yarn (0.0 to 1.0).

        This demonstrates how an LLM might score pattern-yarn combinations.
        """
        score = 0.5  # baseline

        # Yarn weight compatibility
        if pattern_category == "lace":
            if yarn_weight in [YarnWeight.FINGERING, YarnWeight.SPORT]:
                score += 0.3
            elif yarn_weight == YarnWeight.DK:
                score += 0.1
            else:
                score -= 0.2

        elif pattern_category == "cable":
            if yarn_weight in [YarnWeight.DK, YarnWeight.WORSTED]:
                score += 0.3
            elif yarn_weight == YarnWeight.SPORT:
                score += 0.1
            else:
                score -= 0.1

        elif pattern_category == "basic":
            score += 0.2  # Basic patterns work with most yarns

        # Fiber type compatibility
        if fiber_type == "natural":
            score += 0.1  # Natural fibers generally work well

        # Keep score in bounds
        return max(0.0, min(1.0, score))

    def get_knowledge_for_llm(self, topic: str) -> str:
        """
        Get formatted knowledge for LLM consumption.

        This method would be called by LLM agents to get relevant knowledge
        for reasoning about fabric properties.
        """
        if topic == "gauge":
            return "\n".join(self.gauge_principles.values())
        elif topic == "drape":
            return "\n".join(self.drape_principles.values())
        elif topic == "warmth":
            return "\n".join(self.warmth_principles.values())
        elif topic == "construction":
            return "\n".join(self.construction_principles.values())
        elif topic == "all":
            all_knowledge = []
            all_knowledge.extend(self.gauge_principles.values())
            all_knowledge.extend(self.drape_principles.values())
            all_knowledge.extend(self.warmth_principles.values())
            all_knowledge.extend(self.construction_principles.values())
            return "\n".join(all_knowledge)
        else:
            return "No knowledge available for this topic"
