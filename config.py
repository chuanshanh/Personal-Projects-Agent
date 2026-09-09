"""Small provider switch; environment overrides local Streamlit secrets."""
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


def load_settings():
    path = Path(__file__).parent / '.streamlit' / 'secrets.toml'
    values = tomllib.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    return {**values, **os.environ}


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    base_url: str
    api_key: str = field(repr=False)

    @classmethod
    def from_settings(cls, values):
        provider = str(values.get('LLM_PROVIDER', 'openai')).strip().lower()
        is_openai = provider == 'openai'
        return cls(provider=provider,
                   model=str(values.get('LLM_MODEL', values.get('OPENAI_MODEL', 'gpt-4.1-mini') if is_openai else '')).strip(),
                   base_url=str(values.get('LLM_BASE_URL', 'https://api.openai.com/v1' if is_openai else '')).strip(),
                   api_key=str(values.get('LLM_API_KEY', values.get('OPENAI_API_KEY', '') if is_openai else '')).strip())

    def problem(self):
        if self.provider not in ('openai', 'openai-compatible'):
            return 'LLM_PROVIDER 请选择 openai 或 openai-compatible。'
        if not self.model:
            return '请配置 LLM_MODEL。'
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            return '请配置有效的 LLM_BASE_URL（API 根地址，不包含密钥、查询参数或片段）。'
        if not self.api_key or self.api_key == 'your-api-key':
            return '请在本地 secrets 或环境变量中配置 LLM_API_KEY（也兼容 OPENAI_API_KEY）。'
        return None
