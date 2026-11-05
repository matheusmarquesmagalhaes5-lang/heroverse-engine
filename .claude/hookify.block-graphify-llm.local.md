---
name: block-graphify-llm-and-installs
enabled: true
event: bash
action: block
pattern: \bgraphify\s+(extract|label|add|clone|watch|hook|install|uninstall|merge-driver)\b|\bgraphify\b[^|;&\n]*--(backend(?![= ]+none\b)|dedup-llm|obsidian)|\bGRAPHIFY_BACKEND=(?!none\b)|graphify\.llm\b|extract_corpus_parallel
---

**Bloqueado: o Graphify aqui é só o mapa de código local** (`GRAPHIFY_BACKEND=none graphify update .`, depois
`graphify query|affected|path|explain`). `extract`/`label`/`add`/`--backend` usam um LLM (Bedrock, Gemini ou
`claude -p`), o que seria gasto novo ou envio de documentos; `install`/`hook`/`watch` alteram a configuração.
Ver `migration/OPERATIONS.md`, "Engineering workflow".
