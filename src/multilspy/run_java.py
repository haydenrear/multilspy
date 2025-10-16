from multilspy import SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger

config = MultilspyConfig.from_dict({"code_language": "java"}) # Also supports "python", "rust", "csharp", "typescript", "javascript", "go", "dart", "ruby"
logger = MultilspyLogger()
lsp = SyncLanguageServer.create(config, logger, "/abs/path/to/project/root/")

with lsp.start_server():
    result = lsp.request_text_document_diagnostics(None)
