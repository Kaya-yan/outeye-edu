"""
入库错误码定义

processor 在解析/向量化阶段捕获异常，映射为结构化错误码，供前端显示友好提示。
"""

ERROR_SCANNED_PDF = "SCANNED_PDF"
ERROR_FILE_TOO_LARGE = "FILE_TOO_LARGE"
ERROR_WORD_PARSE_FAILED = "WORD_PARSE_FAILED"
ERROR_TEXT_ENCODING_FAILED = "TEXT_ENCODING_FAILED"
ERROR_EMBEDDING_WAITING = "EMBEDDING_WAITING"
ERROR_EMBEDDING_FAILED = "EMBEDDING_FAILED"

ERROR_MESSAGES = {
    ERROR_SCANNED_PDF: "扫描件无法自动解析，请上传可编辑文档或手动粘贴文本",
    ERROR_FILE_TOO_LARGE: "文件过大，请压缩或分段上传（上限 20MB）",
    ERROR_WORD_PARSE_FAILED: "文件解析失败，请检查格式或另存为 DOCX/PDF",
    ERROR_TEXT_ENCODING_FAILED: "文本编码错误，请转换为 UTF-8 后重试",
    ERROR_EMBEDDING_WAITING: "模型加载中，请稍后刷新",
    ERROR_EMBEDDING_FAILED: "向量化失败，请稍后重试",
}


class IngestionError(Exception):
    """带结构化错误码的入库异常"""

    def __init__(self, error_code: str, detail: str = ""):
        self.error_code = error_code
        self.detail = detail
        super().__init__(ERROR_MESSAGES.get(error_code, detail or "入库失败"))
