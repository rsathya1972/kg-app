"""
Tests for relationship extraction logic.
All Claude API calls are mocked — no real API calls made.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.extraction.base import Entity, ExtractionResult, RELATIONSHIP_TYPES
from app.extraction.mock_extractor import MockRelationExtractor
from app.extraction.relation_extractor import RelationExtractor, _deduplicate, _strip_fences


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_entity(name: str, label: str = "Company") -> Entity:
    return Entity(text=name, label=label)


ACME = make_entity("Acme Corp", "Company")
ALICE = make_entity("Alice Smith", "Person")
K8S = make_entity("Kubernetes", "Technology")
GDPR = make_entity("GDPR", "Regulation")
NYC = make_entity("New York", "Location")


# ── Test 1: deduplication keeps highest confidence ────────────────────────────

def test_deduplication_keeps_highest_confidence():
    from app.extraction.base import Relation

    rels = [
        Relation(subject_id="a", predicate="WORKS_FOR", object_id="b", confidence=0.6),
        Relation(subject_id="a", predicate="WORKS_FOR", object_id="b", confidence=0.9),
        Relation(subject_id="a", predicate="WORKS_FOR", object_id="b", confidence=0.4),
    ]
    result = _deduplicate(rels)
    assert len(result) == 1
    assert result[0].confidence == 0.9


def test_deduplication_preserves_different_types():
    from app.extraction.base import Relation

    rels = [
        Relation(subject_id="a", predicate="WORKS_FOR", object_id="b", confidence=0.8),
        Relation(subject_id="a", predicate="OWNS", object_id="b", confidence=0.8),
    ]
    result = _deduplicate(rels)
    assert len(result) == 2


# ── Test 2: entity validation filters unknown names ───────────────────────────

@pytest.mark.asyncio
async def test_entity_validation_filters_unknown_names():
    mock_response = json.dumps({
        "relations": [
            {
                "source": "Acme Corp",
                "type": "USES",
                "target": "Unknown System XYZ",  # not in entity list
                "evidence": "Acme Corp uses Unknown System XYZ",
                "confidence": 0.9,
            }
        ]
    })

    extractor = RelationExtractor()
    with patch(
        "app.extraction.relation_extractor.anthropic_client.complete",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await extractor.extract_from_entities(
            "doc-1",
            "Acme Corp uses Unknown System XYZ in their operations.",
            [ACME, K8S],
        )

    assert len(result.relations) == 0


# ── Test 3: chunks with fewer than 2 entities are skipped ────────────────────

@pytest.mark.asyncio
async def test_skips_chunk_with_fewer_than_two_entities():
    """A chunk containing only one known entity should not trigger Claude."""
    extractor = RelationExtractor(chunk_size=50, overlap=5)

    call_count = 0

    async def mock_complete(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return json.dumps({"relations": []})

    with patch(
        "app.extraction.relation_extractor.anthropic_client.complete",
        new=mock_complete,
    ):
        # Text mentions only ACME, never K8S
        await extractor.extract_from_entities(
            "doc-2",
            "Acme Corp is a large enterprise. They have many employees. The company is growing.",
            [ACME, K8S],
        )

    assert call_count == 0


# ── Test 4: mock extractor returns valid ExtractionResult shape ───────────────

@pytest.mark.asyncio
async def test_mock_extractor_returns_valid_shape():
    extractor = MockRelationExtractor()
    entities = [ACME, ALICE, K8S, GDPR, NYC]

    result = await extractor.extract_from_entities("doc-3", "Some text.", entities)

    assert isinstance(result, ExtractionResult)
    assert result.document_id == "doc-3"
    assert result.model_used == "mock"
    assert isinstance(result.relations, list)
    # Every relation should have non-empty subject_id and object_id
    for rel in result.relations:
        assert rel.subject_id
        assert rel.object_id
        assert rel.predicate in RELATIONSHIP_TYPES
        assert 0.0 <= (rel.confidence or 0.0) <= 1.0


@pytest.mark.asyncio
async def test_mock_extractor_handles_fewer_than_two_entities():
    extractor = MockRelationExtractor()
    result = await extractor.extract_from_entities("doc-4", "text", [ACME])
    assert result.relations == []


# ── Test 5: _strip_fences removes markdown code fences ───────────────────────

def test_strip_fences_removes_json_fence():
    raw = "```json\n{\"relations\": []}\n```"
    assert _strip_fences(raw) == '{"relations": []}'


def test_strip_fences_removes_plain_fence():
    raw = "```\n{\"relations\": []}\n```"
    assert _strip_fences(raw) == '{"relations": []}'


def test_strip_fences_passthrough_clean_json():
    raw = '{"relations": []}'
    assert _strip_fences(raw) == '{"relations": []}'


# ── Test 6: invalid relationship types are filtered out ──────────────────────

@pytest.mark.asyncio
async def test_relationship_type_validation_filters_unknown():
    mock_response = json.dumps({
        "relations": [
            {
                "source": "Acme Corp",
                "type": "ACQUIRED_BY",  # not in RELATIONSHIP_TYPES
                "target": "Kubernetes",
                "evidence": "Acme Corp acquired Kubernetes.",
                "confidence": 0.9,
            },
            {
                "source": "Acme Corp",
                "type": "USES",  # valid
                "target": "Kubernetes",
                "evidence": "Acme Corp uses Kubernetes for deployments.",
                "confidence": 0.85,
            },
        ]
    })

    extractor = RelationExtractor()
    with patch(
        "app.extraction.relation_extractor.anthropic_client.complete",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await extractor.extract_from_entities(
            "doc-5",
            "Acme Corp uses Kubernetes for their cloud deployments.",
            [ACME, K8S],
        )

    assert len(result.relations) == 1
    assert result.relations[0].predicate == "USES"
