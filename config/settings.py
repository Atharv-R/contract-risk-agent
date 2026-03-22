"""
Centralized configuration — loads from .env, validates with Pydantic.
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- LLM ---
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-2.0-flash")
    llm_temperature: float = Field(default=0.1)  # Low temp for consistency
    llm_max_tokens: int = Field(default=4096)

    # --- Embeddings ---
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384)

    # --- Vector Store ---
    vectorstore_path: str = Field(default="./data/vectorstore")
    clause_library_path: str = Field(default="./clause_library")
    collection_name: str = Field(default="clause_library")

    # --- Risk Scoring ---
    high_risk_threshold: float = Field(default=0.7)
    medium_risk_threshold: float = Field(default=0.4)

    # --- Chunking ---
    chunk_size: int = Field(default=1500)  # chars per chunk
    chunk_overlap: int = Field(default=200)

    # --- Paths ---
    sample_contracts_path: str = Field(default="./data/sample_contracts")
    output_path: str = Field(default="./data/outputs")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def vectorstore_dir(self) -> Path:
        path = Path(self.vectorstore_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def clause_library_dir(self) -> Path:
        return Path(self.clause_library_path)

    @property
    def output_dir(self) -> Path:
        path = Path(self.output_path)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Singleton instance
settings = Settings()