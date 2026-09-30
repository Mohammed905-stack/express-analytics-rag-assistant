import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    api_key: str = ''
    model: str = 'gemini-3.5-flash-lite'
    embedding_model: str = 'gemini-embedding-001'
    dimensions: int = 768
    top_k: int = 4
    max_retries: int = 1
    check_grounding: bool = True
    data_dir: Path = ROOT / 'data'

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / '.env')
        settings = cls(
            api_key=os.getenv('GEMINI_API_KEY', '').strip(),
            model=os.getenv('GEMINI_MODEL', cls.model),
            embedding_model=os.getenv('EMBEDDING_MODEL', cls.embedding_model),
            dimensions=int(os.getenv('EMBEDDING_DIMENSIONS', '768')),
            top_k=int(os.getenv('TOP_K', '4')),
            max_retries=int(os.getenv('MAX_RETRIES', '1')),
            check_grounding=os.getenv('CHECK_GROUNDING', 'true').lower() == 'true',
            data_dir=ROOT / os.getenv('DATA_DIR', 'data'),
        )
        if settings.dimensions not in (768, 1536, 3072):
            raise ValueError('EMBEDDING_DIMENSIONS must be 768, 1536 or 3072')
        if not 1 <= settings.top_k <= 10 or not 0 <= settings.max_retries <= 3:
            raise ValueError('TOP_K must be 1..10 and MAX_RETRIES must be 0..3')
        return settings
