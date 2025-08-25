# User Guide

## Legal Dashboard Usage

Launch the Streamlit application to access the legal dashboard:

```bash
python run.py  # or: streamlit run main.py
```

The dashboard displays detected entities, template information and
recommendations. Use the performance dashboard (`perf_dashboard.py`) to
inspect anonymization metrics.

## Template Configuration

Templates live in `src/config.py` under the `LegalTemplates` registry. Each
entry defines:

- `entities`: types that must be anonymized.
- `preserve`: entities that should remain visible.
- `keywords`: terms used for auto‑detection.

Add new templates by extending `LegalTemplates.LEGAL_TEMPLATES` and provide at
least a list of keywords.

## Ollama Setup

The `OllamaLegalAnalyzer` optionally connects to a local Ollama server for
advanced document analysis. Install and start the server:

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama run llama3  # download a model
ollama serve       # start the service
```

Adjust the base URL or model when creating `EnhancedDocumentAnonymizer` or
`OllamaLegalAnalyzer`:

```python
from src.enhanced_anonymizer import EnhancedDocumentAnonymizer
anonymizer = EnhancedDocumentAnonymizer(ollama_base_url="http://localhost:11434", ollama_model="llama3")
```

If the server is unavailable the application gracefully falls back to regex
processing.

