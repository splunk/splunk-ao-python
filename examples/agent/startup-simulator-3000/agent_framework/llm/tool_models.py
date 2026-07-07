from typing import Any

from pydantic import BaseModel, Field


class TextAnalysis(BaseModel):
    """Structured output for text analysis"""

    complexity_score: float = Field(ge=0.0, le=1.0)
    readability_level: str
    main_topics: list[str]
    key_points: list[str]
    analysis_summary: str
    language_metrics: dict[str, Any]

    @classmethod
    def model_json_schema(cls) -> dict[str, Any]:
        """Get JSON schema with example"""
        schema = super().model_json_schema()
        schema["examples"] = [
            {
                "complexity_score": 0.75,
                "readability_level": "Advanced",
                "main_topics": ["artificial intelligence", "neural networks"],
                "key_points": [
                    "Discusses deep learning architectures",
                    "Covers training methodologies",
                    "Addresses performance optimization",
                ],
                "analysis_summary": "Technical text focusing on advanced AI concepts",
                "language_metrics": {"sentence_count": 15, "average_sentence_length": 20, "vocabulary_richness": 0.8},
            }
        ]
        return schema


class KeywordExtraction(BaseModel):
    """Structured output for keyword extraction"""

    keywords: list[str] = Field(min_items=1)
    importance_scores: dict[str, float]
    categories: dict[str, list[str]]
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    context_relevance: str

    @classmethod
    def model_json_schema(cls) -> dict[str, Any]:
        """Get JSON schema with example"""
        schema = super().model_json_schema()
        schema["examples"] = [
            {
                "keywords": ["machine learning", "neural networks", "optimization"],
                "importance_scores": {"machine learning": 0.9, "neural networks": 0.85, "optimization": 0.7},
                "categories": {"technical": ["machine learning", "neural networks"], "methodology": ["optimization"]},
                "extraction_confidence": 0.85,
                "context_relevance": "High relevance to AI/ML domain",
            }
        ]
        return schema
