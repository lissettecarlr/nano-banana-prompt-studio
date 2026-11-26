import pytest

from nano_banana.core import Change
from nano_banana.core.prompt import (
    PromptParseError,
    apply_changes,
    diff_documents,
    parse_ai_document,
    strip_code_fences,
)

# ---------------- AI 输出解析 ----------------


@pytest.mark.parametrize(
    "content",
    [
        '{"风格模式": "插画"}',
        '```json\n{"风格模式": "插画"}\n```',
        '```\n{"风格模式": "插画"}\n```',
        '好的，这是结果：\n```json\n{"风格模式": "插画"}\n```\n希望有帮助',
        '这是结果 {"风格模式": "插画"} 以上',
        '```json\n{"风格模式": "插画"}',  # 流被截断，围栏没闭合
    ],
)
def test_parse_tolerates_fences_and_chatter(content):
    assert parse_ai_document(content) == {"风格模式": "插画"}


def test_parse_upgrades_legacy_shapes():
    document = parse_ai_document('{"场景": {"主体": {"表情与动作": "挥手"}}}')
    assert document["场景"]["主体"]["表情与动作"] == {"情绪": "", "动作": "挥手"}


@pytest.mark.parametrize("content", ["", "   ", "不是 JSON", "[1, 2]", '{"a": ', "```json\n```"])
def test_parse_rejects_non_documents(content):
    with pytest.raises(PromptParseError):
        parse_ai_document(content)


def test_strip_code_fences_keeps_plain_text():
    assert strip_code_fences("  hello  ") == "hello"
    assert strip_code_fences("```json\n{}\n```") == "{}"


# ---------------- 差异 ----------------


def test_diff_reports_leaf_changes_in_document_order():
    old = {"风格模式": "插画", "场景": {"环境": {"光线": "柔光", "天气氛围": "晴"}}, "多余": "x"}
    new = {"风格模式": "写实", "场景": {"环境": {"光线": "柔光", "天气氛围": "雨"}}, "新增": "y"}

    changes = diff_documents(old, new)

    assert [(change.label, change.kind) for change in changes] == [
        ("风格模式", "changed"),
        ("场景 > 环境 > 天气氛围", "changed"),
        ("多余", "removed"),
        ("新增", "added"),
    ]
    assert changes[0].old == "插画" and changes[0].new == "写实"


def test_diff_treats_missing_and_empty_as_equal():
    assert diff_documents({"a": ""}, {}) == []
    assert diff_documents({}, {"a": "", "b": [], "c": None}) == []
    assert diff_documents({"a": {"b": ""}}, {"a": {}}) == []
    assert diff_documents(None, None) == []


def test_apply_changes_only_applies_the_selected_ones():
    old = {"风格模式": "插画", "场景": {"环境": {"光线": "柔光"}}, "多余": "x"}
    new = {"风格模式": "写实", "场景": {"环境": {"光线": "逆光"}}, "新增": {"k": "v"}}
    changes = diff_documents(old, new)

    assert apply_changes(old, changes) == new
    assert apply_changes(old, []) == old

    style_only = [change for change in changes if change.path == ("风格模式",)]
    partial = apply_changes(old, style_only)
    assert partial == {"风格模式": "写实", "场景": {"环境": {"光线": "柔光"}}, "多余": "x"}
    assert old["风格模式"] == "插画"  # 入参不被修改


def test_change_roundtrips_through_json_dict():
    change = Change(("场景", "环境", "光线"), "changed", old="柔光", new="逆光")
    data = change.to_dict()
    assert data["path"] == ["场景", "环境", "光线"]
    assert data["label"] == "场景 > 环境 > 光线"
    assert Change.from_dict(data) == change

    for bad in ({"path": [], "kind": "added"}, {"path": ["a"], "kind": "nope"}, {"path": "a"}):
        with pytest.raises(ValueError):
            Change.from_dict(bad)
