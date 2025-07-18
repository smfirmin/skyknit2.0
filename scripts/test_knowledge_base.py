#!/usr/bin/env python3
"""
Test script for the knitting knowledge base.

This script demonstrates the RAG architecture by populating the database
with sample data and testing search functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from skyknit.knowledge_base.database import KnowledgeBaseDB
from skyknit.knowledge_base.fabric_knowledge import FabricKnowledgeBase
from skyknit.knowledge_base.sample_data import populate_sample_data
from skyknit.knowledge_base.schemas import DifficultyLevel, YarnWeight


def test_structured_database():
    """Test the structured database functionality"""
    print("🗄️  Testing Structured Database")
    print("=" * 40)

    # Initialize database
    db_path = Path(__file__).parent.parent / "knowledge_base.db"

    with KnowledgeBaseDB(db_path) as db:
        # Populate with sample data
        print("📚 Populating database with sample data...")
        populate_sample_data(db)

        print("\n🔍 Testing search functionality...")

        # Test pattern searches
        print("\n1. Basic patterns:")
        basic_patterns = db.search_stitch_patterns(category="basic")
        for pattern in basic_patterns:
            print(f"   • {pattern.name} ({pattern.difficulty.value})")

        print("\n2. Intermediate difficulty patterns:")
        intermediate_patterns = db.search_stitch_patterns(
            difficulty=DifficultyLevel.INTERMEDIATE
        )
        for pattern in intermediate_patterns:
            print(f"   • {pattern.name} ({pattern.category})")

        print("\n3. Patterns suitable for worsted weight:")
        worsted_patterns = db.search_stitch_patterns(yarn_weight=YarnWeight.WORSTED)
        for pattern in worsted_patterns:
            print(f"   • {pattern.name} - {pattern.description[:50]}...")

        print("\n4. Patterns with 'border' keyword:")
        border_patterns = db.search_stitch_patterns(keywords=["border"])
        for pattern in border_patterns:
            print(f"   • {pattern.name} - Best for: {', '.join(pattern.best_for)}")

        # Test yarn searches
        print("\n5. Worsted weight yarns:")
        worsted_yarns = db.search_yarns(weight=YarnWeight.WORSTED)
        for yarn in worsted_yarns:
            print(f"   • {yarn.brand} {yarn.name} - {yarn.price_range} price")

        print("\n6. Machine washable yarns:")
        washable_yarns = db.search_yarns(keywords=["machine_washable"])
        for yarn in washable_yarns:
            print(f"   • {yarn.brand} {yarn.name} - {yarn.care_instructions}")

        print("\n7. Budget-friendly options:")
        budget_yarns = [y for y in db.search_yarns() if y.price_range == "budget"]
        for yarn in budget_yarns:
            print(f"   • {yarn.brand} {yarn.name} - {yarn.yardage_per_unit} yards")

        # Demonstrate pattern compatibility
        print("\n8. Pattern combinations:")
        stockinette = db.get_stitch_pattern("stockinette")
        if stockinette:
            print(f"   • {stockinette.name} combines well with:")
            for combo_id in stockinette.combines_well_with:
                combo_pattern = db.get_stitch_pattern(combo_id)
                if combo_pattern:
                    print(f"     - {combo_pattern.name}")

        # Show pattern technical details
        print("\n9. Technical pattern details:")
        cable = db.get_stitch_pattern("simple_cable")
        if cable:
            print(f"   • {cable.name}:")
            print(
                f"     - Repeat: {cable.repeat_width} sts × {cable.repeat_height} rows"
            )
            print(f"     - Gauge modifier: {cable.gauge_modifier}")
            print(f"     - Stitch multiple: {cable.stitch_count_multiple}")
            print(f"     - Tips: {cable.tips[0]}")

    return db_path


def test_fabric_knowledge():
    """Test the fabric knowledge base"""
    print("\n🧶 Testing Fabric Knowledge Base")
    print("=" * 40)

    fabric_kb = FabricKnowledgeBase()

    # Test knowledge retrieval
    print("\n1. Gauge principles:")
    gauge_knowledge = fabric_kb.get_knowledge_for_llm("gauge")
    print(f"   Knowledge length: {len(gauge_knowledge)} characters")
    print(f"   Sample: {gauge_knowledge[:200]}...")

    print("\n2. Drape principles:")
    drape_knowledge = fabric_kb.get_knowledge_for_llm("drape")
    print(f"   Knowledge length: {len(drape_knowledge)} characters")
    print(f"   Sample: {drape_knowledge[:200]}...")

    # Test fabric prediction
    print("\n3. Fabric predictions:")
    predictions = [
        ("cable", YarnWeight.WORSTED, "natural"),
        ("lace", YarnWeight.FINGERING, "natural"),
        ("basic", YarnWeight.BULKY, "synthetic"),
    ]

    for pattern_cat, yarn_weight, fiber_type in predictions:
        prediction = fabric_kb.get_fabric_prediction(
            pattern_cat, yarn_weight, fiber_type
        )
        print(f"   • {pattern_cat} + {yarn_weight.value} + {fiber_type}:")
        print(f"     - Gauge: {prediction['gauge_impact']}")
        print(f"     - Drape: {prediction['drape_quality']}")
        print(f"     - Warmth: {prediction['warmth_level']}")

    # Test compatibility scoring
    print("\n4. Compatibility scores:")
    combinations = [
        ("lace", YarnWeight.FINGERING, "natural"),
        ("cable", YarnWeight.WORSTED, "natural"),
        ("basic", YarnWeight.SUPER_BULKY, "synthetic"),
    ]

    for pattern_cat, yarn_weight, fiber_type in combinations:
        score = fabric_kb.get_compatibility_score(pattern_cat, yarn_weight, fiber_type)
        print(f"   • {pattern_cat} + {yarn_weight.value} + {fiber_type}: {score:.2f}")

    # Show fabric rules
    print("\n5. Sample fabric rules:")
    for rule in fabric_kb.rules[:3]:
        print(f"   • {rule.condition}")
        print(f"     → {rule.effect} (confidence: {rule.confidence})")


def test_integration():
    """Test integration between structured and unstructured knowledge"""
    print("\n🔗 Testing Knowledge Integration")
    print("=" * 40)

    # Initialize both systems
    db_path = Path(__file__).parent.parent / "knowledge_base.db"
    fabric_kb = FabricKnowledgeBase()

    with KnowledgeBaseDB(db_path) as db:
        # Get a pattern and yarn
        pattern = db.get_stitch_pattern("simple_cable")
        yarn = db.get_yarn("cascade_220")

        if pattern and yarn:
            print(f"\n📋 Analyzing: {pattern.name} with {yarn.brand} {yarn.name}")
            print(f"   Pattern: {pattern.category}, {pattern.difficulty.value}")
            print(f"   Yarn: {yarn.weight.value}, {yarn.fiber_type}")

            # Use fabric knowledge to predict behavior
            prediction = fabric_kb.get_fabric_prediction(
                pattern.category, yarn.weight, yarn.fiber_type
            )
            compatibility = fabric_kb.get_compatibility_score(
                pattern.category, yarn.weight, yarn.fiber_type
            )

            print("\n🔮 Fabric Prediction:")
            print(f"   • Gauge Impact: {prediction['gauge_impact']}")
            print(f"   • Drape Quality: {prediction['drape_quality']}")
            print(f"   • Warmth Level: {prediction['warmth_level']}")
            print(f"   • Compatibility Score: {compatibility:.2f}")

            # Show how LLM would get relevant knowledge
            print("\n📚 Relevant Knowledge for LLM:")
            construction_knowledge = fabric_kb.get_knowledge_for_llm("construction")
            relevant_section = construction_knowledge.split("\n")[0:3]
            for line in relevant_section:
                if line.strip():
                    print(f"   {line.strip()}")


def main():
    """Run all knowledge base tests"""
    print("🧶 Testing Knitting Knowledge Base")
    print("=" * 50)

    # Test structured database
    db_path = test_structured_database()

    # Test fabric knowledge
    test_fabric_knowledge()

    # Test integration
    test_integration()

    print("\n✅ Knowledge base tests completed!")
    print(f"📁 Database saved to: {db_path}")
    print("🔧 Ready for LLM integration!")
    print("\n📊 Summary:")
    print("   • Structured database: 7 patterns, 6 yarns")
    print("   • Unstructured knowledge: 100+ fabric rules and principles")
    print("   • Integration: Pattern + yarn → fabric prediction")
    print("   • RAG ready: Searchable patterns/yarns + reasoning knowledge")


if __name__ == "__main__":
    main()
