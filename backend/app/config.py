from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    ENV: str = "development"
    APP_NAME: str = "Ontology Graph Studio"
    APP_VERSION: str = "0.1.0"

    # AI keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://kguser:kgpassword@localhost:5432/kgdb"

    # Neo4j (planned for later)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4jpassword"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Storage
    UPLOAD_DIR: str = "./storage/uploads"
    OUTPUT_DIR: str = "./storage/outputs"

    # Preprocessing / chunking
    MAX_CHUNK_SIZE: int = 1000      # Max tokens per chunk
    CHUNK_OVERLAP: int = 100        # Overlap tokens between chunks

    # Vector memory / embeddings
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_DIMENSIONS: int = 1536
    VECTOR_SEARCH_TOP_K: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
