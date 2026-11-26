import json

import pytest
from conftest import BUILTIN

from nano_banana.core.storage.presets import PresetStore, safe_preset_name


@pytest.fixture
def store(tmp_path) -> PresetStore:
    return PresetStore(tmp_path / "presets")


def test_category_presets_are_separate_from_global_presets(store):
    assert store.save("完整方案", {"风格模式": "写实"}) == "完整方案"
    assert store.save_category("basic", "写实基础", {"风格模式": "写实"}) == "写实基础"

    assert [item["name"] for item in store.list_all()] == ["完整方案"]
    assert [item["name"] for item in store.list_category("basic")] == ["写实基础"]
    assert store.load_category("basic", "写实基础") == {"风格模式": "写实"}
    assert store.load("完整方案") == {"风格模式": "写实"}


def test_category_presets_are_isolated_by_scope(store):
    assert store.save_category("basic", "常用", {"风格模式": "插画"})
    assert store.save_category("scene", "常用", {"场景": {"环境": {"光线": "柔光"}}})

    assert store.load_category("basic", "常用") == {"风格模式": "插画"}
    assert store.load_category("scene", "常用") == {"场景": {"环境": {"光线": "柔光"}}}
    assert store.delete_category("basic", "常用")
    assert store.load_category("basic", "常用") is None
    assert store.load_category("scene", "常用") is not None


def test_save_returns_the_sanitized_name(store):
    assert safe_preset_name("  a/b\\c:d..e  ") == "abcde"
    assert store.save("../逃逸/名字", {"a": 1}) == "逃逸名字"
    assert [item["name"] for item in store.list_all()] == ["逃逸名字"]
    assert store.save("x", ["not", "a", "dict"]) is None
    assert store.save_category("basic", "///", {"a": 1}) is None


@pytest.mark.parametrize("name", ["../secret", "..", "a/b", "a\\b", "C:secret", "", ".hidden", None])
def test_names_cannot_escape_the_preset_directory(store, tmp_path, name):
    secret = tmp_path / "secret.json"
    secret.write_text('{"leak": true}', encoding="utf-8")

    assert store.load(name) is None
    assert store.delete(name) is False
    assert store.load_category("basic", name) is None
    assert secret.exists()


def test_category_scope_rejects_path_traversal(store, tmp_path):
    assert store.save_category("../outside", "bad", {"value": 1}) is None
    assert store.list_category("../outside") == []
    assert store.load_category("../outside", "bad") is None
    assert not (tmp_path / "outside").exists()


def test_presets_with_unusual_but_harmless_names_still_load(store):
    """用户手动放进目录的文件（名字里带标点）也要能读、能删。"""
    (store.user_dir / "我的预设 v1.2【最终】.json").write_text('{"a": 1}', encoding="utf-8")

    names = [item["name"] for item in store.list_all()]
    assert names == ["我的预设 v1.2【最终】"]
    assert store.load(names[0]) == {"a": 1}
    assert store.delete(names[0])


def test_corrupt_preset_loads_as_none(store):
    (store.user_dir / "坏的.json").write_text("{not json", encoding="utf-8")
    (store.user_dir / "数组.json").write_text("[1]", encoding="utf-8")
    assert store.load("坏的") is None
    assert store.load("数组") is None


def test_builtin_presets_are_seeded_once_and_stay_deleted(tmp_path):
    builtin = tmp_path / "builtin"
    (builtin / "categories" / "basic").mkdir(parents=True)
    (builtin / "默认.json").write_text('{"风格模式": "默认"}', encoding="utf-8")
    (builtin / "categories" / "basic" / "基础.json").write_text('{"风格模式": "基础"}', encoding="utf-8")
    user = tmp_path / "user"

    store = PresetStore(user, builtin)
    assert store.load("默认") == {"风格模式": "默认"}
    assert store.load_category("basic", "基础") == {"风格模式": "基础"}
    assert ".seeded" not in [item["name"] for item in store.list_all()]

    # 用户改过的、删掉的，重启后都不会被内置版本覆盖/复活
    store.save("默认", {"风格模式": "我改的"})
    store.delete_category("basic", "基础")
    store = PresetStore(user, builtin)
    assert store.load("默认") == {"风格模式": "我改的"}
    assert store.load_category("basic", "基础") is None

    # 新版本新增的内置预设会出现
    (builtin / "新增.json").write_text('{"风格模式": "新"}', encoding="utf-8")
    store = PresetStore(user, builtin)
    assert store.load("新增") == {"风格模式": "新"}


def test_seeding_never_overwrites_an_existing_user_file(tmp_path):
    builtin = tmp_path / "builtin"
    builtin.mkdir()
    (builtin / "同名.json").write_text('{"来源": "内置"}', encoding="utf-8")
    user = tmp_path / "user"
    user.mkdir()
    (user / "同名.json").write_text('{"来源": "用户"}', encoding="utf-8")

    assert PresetStore(user, builtin).load("同名") == {"来源": "用户"}


# ---------------- 随包发布的内置预设 ----------------

BUILTIN_PRESETS = BUILTIN / "presets"


def _category_presets(scope: str) -> dict[str, dict]:
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in (BUILTIN_PRESETS / "categories" / scope).glob("*.json")
    }


def test_bundled_hoshino_is_a_subject_preset():
    assert not (BUILTIN_PRESETS / "中秋星野（仅角色）.json").exists()
    subject = _category_presets("subject")["中秋星野"]["场景"]["主体"]
    assert subject["整体描述"]
    assert subject["表情与动作"]["动作"] == ""

    prompt_text = json.dumps(subject, ensure_ascii=False)
    for defining_feature in (
        "角色左眼湛蓝、角色右眼金橙",
        "粉色同心圆光环",
        "白兔造型发饰",
        "浅蓝色小鲸鱼吊坠",
        "蓝色蝴蝶结",
    ):
        assert defining_feature in prompt_text
    assert "漂浮的蓝色鲸鱼玩偶" not in prompt_text


def test_bundled_basic_presets_are_a_small_complete_default_set():
    presets = _category_presets("basic")
    assert set(presets) == {
        "现代精致动画",
        "精致游戏CG",
        "电影光影动画",
        "温暖日常动画",
        "清透轻小说插画",
        "半写实厚涂插画",
    }
    for data in presets.values():
        assert set(data) == {"风格模式", "画面气质"}
        assert all(isinstance(value, str) and value.strip() for value in data.values())


def test_bundled_scene_presets_are_a_small_complete_default_set():
    presets = _category_presets("scene")
    assert set(presets) == {
        "盛夏海边车站",
        "春日樱花坡道",
        "黄昏城市天台",
        "雨夜霓虹街道",
        "静谧星空湖畔",
        "暖光窗边房间",
    }
    for data in presets.values():
        scene = data["场景"]
        assert set(scene["环境"]) == {"地点设定", "光线", "天气氛围"}
        assert set(scene["背景"]) == {"描述", "景深"}
        assert all(value.strip() for value in scene["环境"].values())
        assert all(value.strip() for value in scene["背景"].values())


def test_bundled_camera_presets_are_a_small_complete_default_set():
    presets = _category_presets("camera")
    assert set(presets) == {
        "标准全身立绘",
        "半身角色特写",
        "横屏环境壁纸",
        "电影感叙事镜头",
        "动态仰视构图",
        "俯视氛围构图",
    }
    for data in presets.values():
        assert set(data) == {"相机"}
        assert set(data["相机"]) == {"机位角度", "构图", "镜头特性", "传感器画质"}
        assert all(value.strip() for value in data["相机"].values())


def test_bundled_aesthetic_presets_are_a_small_complete_default_set():
    presets = _category_presets("aesthetic")
    assert set(presets) == {
        "通透均衡",
        "柔光低对比",
        "电影冷暖调色",
        "低饱和情绪调色",
        "鲜明视觉强化",
    }
    for data in presets.values():
        aesthetic = data["审美控制"]
        assert set(aesthetic) == {"呈现意图", "材质真实度", "色彩风格"}
        assert isinstance(aesthetic["材质真实度"], list)
        assert all(value.strip() for value in aesthetic["材质真实度"])
        assert set(aesthetic["色彩风格"]) == {"整体色调", "对比度", "特殊效果"}
        assert aesthetic["呈现意图"].strip()
        assert all(value.strip() for value in aesthetic["色彩风格"].values())


def test_every_bundled_preset_only_uses_schema_paths():
    """内置预设里出现 schema 不认识的键 = 这个值永远不会显示在表单里。"""
    from nano_banana.core.prompt import flatten, get_schema, migrate_document, nest

    schema = get_schema()
    overlay_roots = {overlay.path[0] for overlay in schema.overlays}
    for path in BUILTIN_PRESETS.rglob("*.json"):
        data = migrate_document(json.loads(path.read_text(encoding="utf-8")))
        fields_only = {key: value for key, value in data.items() if key not in overlay_roots}
        rebuilt = nest(flatten(fields_only, schema), schema, include_empty=False)
        assert rebuilt == fields_only, path.name
