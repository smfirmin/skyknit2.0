"""
Database interface for the knitting pattern knowledge base.

This module provides the data access layer for storing and retrieving
stitch patterns and yarn information.
"""

import json
import logging
import sqlite3
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from .schemas import (
    DifficultyLevel,
    StitchPattern,
    YarnInfo,
    YarnWeight,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseDB:
    """Database interface for knitting knowledge base"""

    def __init__(self, db_path: str | Path = "knowledge_base.db"):
        """Initialize database connection and create tables if needed"""
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._create_tables()

    def _create_tables(self):
        """Create all database tables"""
        cursor = self.conn.cursor()

        # Stitch patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stitch_patterns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                repeat_width INTEGER NOT NULL,
                repeat_height INTEGER NOT NULL,
                instructions TEXT NOT NULL,  -- JSON array
                chart TEXT,
                gauge_modifier REAL DEFAULT 1.0,
                recommended_yarn_weights TEXT,  -- JSON array
                lies_flat BOOLEAN DEFAULT TRUE,
                has_curl BOOLEAN DEFAULT FALSE,
                stretch_horizontal REAL DEFAULT 1.0,
                stretch_vertical REAL DEFAULT 1.0,
                best_for TEXT,  -- JSON array
                combines_well_with TEXT,  -- JSON array
                stitch_count_multiple INTEGER DEFAULT 1,
                edge_stitches_needed INTEGER DEFAULT 0,
                requires_border BOOLEAN DEFAULT FALSE,
                description TEXT DEFAULT '',
                tips TEXT,  -- JSON array
                common_mistakes TEXT,  -- JSON array
                variations TEXT,  -- JSON array
                embedding TEXT,  -- JSON array of floats
                keywords TEXT,  -- JSON array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Yarn information table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yarn_info (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                weight TEXT NOT NULL,
                fiber_content TEXT NOT NULL,  -- JSON object
                fiber_type TEXT NOT NULL,
                yardage_per_unit INTEGER NOT NULL,
                unit_weight_grams INTEGER NOT NULL,
                recommended_needle_size TEXT NOT NULL,
                standard_gauge_stitches INTEGER NOT NULL,
                standard_gauge_rows INTEGER NOT NULL,
                gauge_needle_size TEXT NOT NULL,
                care_instructions TEXT,  -- JSON array
                machine_washable BOOLEAN DEFAULT FALSE,
                superwash BOOLEAN DEFAULT FALSE,
                ease_of_working TEXT DEFAULT 'intermediate',
                drape TEXT DEFAULT 'medium',
                warmth TEXT DEFAULT 'medium',
                durability TEXT DEFAULT 'medium',
                price_range TEXT DEFAULT 'medium',
                availability TEXT DEFAULT 'common',
                colors_available TEXT,  -- JSON array
                best_for_patterns TEXT,  -- JSON array
                not_recommended_for TEXT,  -- JSON array
                embedding TEXT,  -- JSON array of floats
                keywords TEXT,  -- JSON array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Construction techniques table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS construction_techniques (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                best_for TEXT,  -- JSON array
                yarn_suitability TEXT,  -- JSON array
                description TEXT DEFAULT '',
                step_by_step TEXT,  -- JSON array
                tips TEXT,  -- JSON array
                alternatives TEXT,  -- JSON array
                embedding TEXT,  -- JSON array of floats
                keywords TEXT,  -- JSON array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for better search performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_patterns_category ON stitch_patterns(category)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_patterns_difficulty ON stitch_patterns(difficulty)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_yarn_weight ON yarn_info(weight)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_yarn_brand ON yarn_info(brand)")

        self.conn.commit()

    def _serialize_json_fields(self, obj: Any) -> dict[str, Any]:
        """Convert dataclass to dict with JSON serialization for list/dict fields"""
        data = asdict(obj) if hasattr(obj, "__dataclass_fields__") else obj

        # Convert lists and dicts to JSON strings
        for key, value in data.items():
            if isinstance(value, list | dict):
                # Convert enum values in lists to strings
                if isinstance(value, list):
                    serialized_list = []
                    for item in value:
                        if isinstance(item, DifficultyLevel | YarnWeight):
                            serialized_list.append(item.value)
                        else:
                            serialized_list.append(item)
                    data[key] = json.dumps(serialized_list)
                else:
                    data[key] = json.dumps(value)
            elif isinstance(value, DifficultyLevel | YarnWeight):
                data[key] = value.value

        return data

    def _deserialize_json_fields(self, data: dict[str, Any], target_class) -> Any:
        """Convert database row to dataclass with JSON deserialization"""
        # Get field types from dataclass
        field_types = {f.name: f.type for f in fields(target_class)}

        # Filter out database-only fields
        filtered_data = {}
        for key, value in data.items():
            if key in ["created_at", "updated_at"]:
                continue  # Skip database timestamp fields
            if key in field_types:
                filtered_data[key] = value

        # Deserialize JSON fields
        for key, value in filtered_data.items():
            if value is None:
                continue

            field_type = field_types.get(key)
            if field_type and hasattr(field_type, "__origin__"):
                if field_type.__origin__ is list:
                    try:
                        filtered_data[key] = (
                            json.loads(value) if isinstance(value, str) else value
                        )
                    except json.JSONDecodeError:
                        filtered_data[key] = []
                elif field_type.__origin__ is dict:
                    try:
                        filtered_data[key] = (
                            json.loads(value) if isinstance(value, str) else value
                        )
                    except json.JSONDecodeError:
                        filtered_data[key] = {}

        # Convert enum fields
        if "difficulty" in filtered_data and isinstance(
            filtered_data["difficulty"], str
        ):
            filtered_data["difficulty"] = DifficultyLevel(filtered_data["difficulty"])
        if "weight" in filtered_data and isinstance(filtered_data["weight"], str):
            filtered_data["weight"] = YarnWeight(filtered_data["weight"])

        return target_class(**filtered_data)

    # Stitch Pattern methods
    def add_stitch_pattern(self, pattern: StitchPattern) -> None:
        """Add a new stitch pattern to the database"""
        cursor = self.conn.cursor()
        data = self._serialize_json_fields(pattern)

        placeholders = ", ".join(["?" for _ in data])
        columns = ", ".join(data.keys())

        cursor.execute(
            f"INSERT OR REPLACE INTO stitch_patterns ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        self.conn.commit()
        logger.info(f"Added stitch pattern: {pattern.name}")

    def get_stitch_pattern(self, pattern_id: str) -> StitchPattern | None:
        """Get a stitch pattern by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM stitch_patterns WHERE id = ?", (pattern_id,))
        row = cursor.fetchone()

        if row:
            return self._deserialize_json_fields(dict(row), StitchPattern)
        return None

    def search_stitch_patterns(
        self,
        category: str | None = None,
        difficulty: DifficultyLevel | None = None,
        yarn_weight: YarnWeight | None = None,
        keywords: list[str] | None = None,
    ) -> list[StitchPattern]:
        """Search stitch patterns by various criteria"""
        cursor = self.conn.cursor()
        query = "SELECT * FROM stitch_patterns WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if difficulty:
            query += " AND difficulty = ?"
            params.append(difficulty.value)

        if yarn_weight:
            query += " AND recommended_yarn_weights LIKE ?"
            params.append(f'%"{yarn_weight.value}"%')

        if keywords:
            for keyword in keywords:
                query += " AND (name LIKE ? OR description LIKE ? OR keywords LIKE ?)"
                params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [self._deserialize_json_fields(dict(row), StitchPattern) for row in rows]

    def get_all_stitch_patterns(self) -> list[StitchPattern]:
        """Get all stitch patterns"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM stitch_patterns ORDER BY name")
        rows = cursor.fetchall()

        return [self._deserialize_json_fields(dict(row), StitchPattern) for row in rows]

    # Yarn methods
    def add_yarn(self, yarn: YarnInfo) -> None:
        """Add a new yarn to the database"""
        cursor = self.conn.cursor()
        data = self._serialize_json_fields(yarn)

        placeholders = ", ".join(["?" for _ in data])
        columns = ", ".join(data.keys())

        cursor.execute(
            f"INSERT OR REPLACE INTO yarn_info ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        self.conn.commit()
        logger.info(f"Added yarn: {yarn.brand} {yarn.name}")

    def get_yarn(self, yarn_id: str) -> YarnInfo | None:
        """Get yarn information by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM yarn_info WHERE id = ?", (yarn_id,))
        row = cursor.fetchone()

        if row:
            return self._deserialize_json_fields(dict(row), YarnInfo)
        return None

    def search_yarns(
        self,
        weight: YarnWeight | None = None,
        brand: str | None = None,
        fiber_type: str | None = None,
        keywords: list[str] | None = None,
    ) -> list[YarnInfo]:
        """Search yarns by various criteria"""
        cursor = self.conn.cursor()
        query = "SELECT * FROM yarn_info WHERE 1=1"
        params = []

        if weight:
            query += " AND weight = ?"
            params.append(weight.value)

        if brand:
            query += " AND brand LIKE ?"
            params.append(f"%{brand}%")

        if fiber_type:
            query += " AND fiber_type = ?"
            params.append(fiber_type)

        if keywords:
            for keyword in keywords:
                query += " AND (name LIKE ? OR brand LIKE ? OR keywords LIKE ?)"
                params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [self._deserialize_json_fields(dict(row), YarnInfo) for row in rows]

    def get_all_yarns(self) -> list[YarnInfo]:
        """Get all yarns"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM yarn_info ORDER BY brand, name")
        rows = cursor.fetchall()

        return [self._deserialize_json_fields(dict(row), YarnInfo) for row in rows]

    def close(self):
        """Close database connection"""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
