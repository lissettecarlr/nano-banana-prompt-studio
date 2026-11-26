"""结构化提示词领域模型：schema、文档、渲染、兼容、差异。纯函数，无 IO 依赖（schema.yaml 除外）。"""

from nano_banana.core.prompt.diff import Change, apply_changes, diff_documents
from nano_banana.core.prompt.document import (
    apply_partial,
    build_document,
    flatten,
    get_at_path,
    get_line_art,
    get_special_requirement,
    nest,
    order_document,
    set_at_path,
    subset,
)
from nano_banana.core.prompt.migrate import migrate_document, normalize_negative_prompt
from nano_banana.core.prompt.parse import PromptParseError, parse_ai_document, strip_code_fences
from nano_banana.core.prompt.render import RenderedPrompt, payload_json, prompt_payload, render_prompt
from nano_banana.core.prompt.schema import (
    PromptCategory,
    PromptField,
    PromptOverlay,
    PromptSchema,
    default_negative_prompt,
    get_schema,
    load_schema,
    overlay_by_id,
)

__all__ = [
    "Change",
    "PromptCategory",
    "PromptField",
    "PromptOverlay",
    "PromptParseError",
    "PromptSchema",
    "RenderedPrompt",
    "apply_changes",
    "apply_partial",
    "build_document",
    "default_negative_prompt",
    "diff_documents",
    "flatten",
    "get_at_path",
    "get_line_art",
    "get_schema",
    "get_special_requirement",
    "load_schema",
    "migrate_document",
    "nest",
    "normalize_negative_prompt",
    "order_document",
    "overlay_by_id",
    "parse_ai_document",
    "payload_json",
    "prompt_payload",
    "render_prompt",
    "set_at_path",
    "strip_code_fences",
    "subset",
]
