"""
Central API router: aggregates all domain sub-routers under /api.
Add new routers here as new modules are implemented.
"""
from fastapi import APIRouter

from app.api.routes import (
    health,
    ingestion,
    extraction,
    entities,
    relationships,
    ontology,
    graph,
    query,
    graphrag,
    validation,
    vector_memory,
    agents,
    learning,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(ingestion.router)
api_router.include_router(extraction.router)
api_router.include_router(entities.router)
api_router.include_router(relationships.router)
api_router.include_router(ontology.router)
api_router.include_router(graph.router)
api_router.include_router(query.router)
api_router.include_router(graphrag.router)
api_router.include_router(validation.router)
api_router.include_router(vector_memory.router)
api_router.include_router(agents.router)
api_router.include_router(learning.router)
