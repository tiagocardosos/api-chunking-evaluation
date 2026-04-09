import enum


class ChunkingStrategy(str, enum.Enum):
    fixed_size = "fixed_size"
    recursive = "recursive"
    sentence = "sentence"
    semantic = "semantic"
    structure_aware = "structure_aware"


class DocType(str, enum.Enum):
    pdf = "pdf"
    xml_lattes = "xml_lattes"
    json_lattes = "json_lattes"


class RetrievalStrategy(str, enum.Enum):
    semantic = "semantic"
    hybrid = "hybrid"


class ExperimentStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
