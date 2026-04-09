# Estratégias de Chunking – Detalhamento Técnico

1. FixedSizeChunker
2. RecursiveCharacterChunker
3. SentenceChunker
4. SemanticChunker
5. StructureAwareChunker (XML Lattes only – parseia tags <dados-gerais>, <artigos>, <producao>, headings)

**Registry:** backend/core/chunking/registry.py (classe abstrata ChunkingStrategy)
