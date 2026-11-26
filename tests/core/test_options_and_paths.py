import yaml
from conftest import BUILTIN, ROOT

from nano_banana.core import Studio, StudioPaths
from nano_banana.core.prompt import get_schema
from nano_banana.core.storage import paths as paths_module
from nano_banana.core.storage.files import atomic_write_text, locked
from nano_banana.core.storage.legacy import import_legacy_user_data
from nano_banana.core.storage.options import OptionsStore

NEGATIVE_TAGS = "反向提示词标签"
DEFAULT_TAG = "水印、签名、文字"


def _store(tmp_path, user=None, builtin=None) -> OptionsStore:
    user_file = tmp_path / "user" / "options.yaml"
    builtin_file = tmp_path / "builtin" / "options.yaml"
    for path, data in ((user_file, user), (builtin_file, builtin)):
        if data is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return OptionsStore(user_file, builtin_file, fallback={NEGATIVE_TAGS: [DEFAULT_TAG]})


# ---------------- 选项 ----------------


def test_old_config_gets_the_default_negative_prompt_tag(tmp_path):
    store = _store(tmp_path, user={"禁止元素": ["旧选项"]})
    assert store.get_field_options(NEGATIVE_TAGS) == [DEFAULT_TAG]


def test_saved_negative_prompt_tags_override_the_default(tmp_path):
    store = _store(tmp_path, user={NEGATIVE_TAGS: ["自定义标签"]})
    assert store.get_field_options(NEGATIVE_TAGS) == ["自定义标签"]


def test_first_custom_tag_keeps_the_default_for_old_configs(tmp_path):
    store = _store(tmp_path, user={"禁止元素": ["旧选项"]})
    store.add_option(NEGATIVE_TAGS, "自定义标签")
    assert store.get_field_options(NEGATIVE_TAGS) == [DEFAULT_TAG, "自定义标签"]


def test_default_tag_can_be_deleted_from_an_old_config(tmp_path):
    store = _store(tmp_path, user={"禁止元素": ["旧选项"]})
    store.remove_option(NEGATIVE_TAGS, DEFAULT_TAG)
    assert store.get_field_options(NEGATIVE_TAGS) == []


def test_user_file_overrides_builtin_per_key_and_only_stores_touched_keys(tmp_path):
    store = _store(tmp_path, builtin={"风格模式": ["插画", "写实"], "光线": ["柔光"], "角色线稿提示词": "内置线稿"})

    assert store.get_field_options("风格模式") == ["插画", "写实"]
    assert store.get_line_art_prompt() == "内置线稿"
    assert not store.user_file.exists()

    store.add_option("风格模式", "厚涂")
    store.add_option("风格模式", "厚涂")  # 重复添加是空操作
    store.remove_option("光线", "不存在")  # 删除不存在的值不落盘
    store.save_line_art_prompt("我的线稿")

    assert store.get_field_options("风格模式") == ["插画", "写实", "厚涂"]
    assert store.get_field_options("光线") == ["柔光"]
    assert store.get_line_art_prompt() == "我的线稿"
    on_disk = yaml.safe_load(store.user_file.read_text(encoding="utf-8"))
    assert on_disk == {"风格模式": ["插画", "写实", "厚涂"], "角色线稿提示词": "我的线稿"}
    # 内置文件是只读的
    assert yaml.safe_load(store.builtin_file.read_text(encoding="utf-8"))["风格模式"] == ["插画", "写实"]


def test_update_option_renames_in_place(tmp_path):
    store = _store(tmp_path, builtin={"风格模式": ["插画", "写实"]})
    store.update_option("风格模式", "插画", "二次元插画")
    assert store.get_field_options("风格模式") == ["二次元插画", "写实"]


def test_corrupt_user_options_fall_back_to_builtin(tmp_path):
    store = _store(tmp_path, builtin={"风格模式": ["插画"]})
    store.user_file.parent.mkdir(parents=True)
    store.user_file.write_text("a: [unclosed", encoding="utf-8")
    assert store.get_field_options("风格模式") == ["插画"]


def test_bundled_options_cover_every_schema_field():
    options = yaml.safe_load((BUILTIN / "options.yaml").read_text(encoding="utf-8"))
    for field in get_schema().iter_fields():
        assert isinstance(options.get(field.widget_key), list), field.widget_key
    assert isinstance(options.get("角色线稿提示词"), str)


# ---------------- 文件工具 ----------------


def test_atomic_write_replaces_content_and_leaves_no_temp_files(tmp_path):
    target = tmp_path / "nested" / "file.txt"
    atomic_write_text(target, "one")
    atomic_write_text(target, "two")
    assert target.read_text(encoding="utf-8") == "two"
    assert [path.name for path in target.parent.iterdir()] == ["file.txt"]


def test_lock_is_reentrant_and_cleans_up(tmp_path):
    target = tmp_path / "file.yaml"
    with locked(target):
        with locked(target):
            atomic_write_text(target, "x")
    assert not list(tmp_path.glob("*.lock"))


# ---------------- 数据目录 ----------------


def test_env_var_overrides_the_user_dir(monkeypatch, tmp_path):
    monkeypatch.setenv(paths_module.HOME_ENV, str(tmp_path / "home"))
    paths = StudioPaths.default()
    assert paths.user == tmp_path / "home"
    assert paths.settings_file == tmp_path / "home" / "config" / "ai_config.yaml"
    assert paths.presets_dir == tmp_path / "home" / "presets"
    assert paths.legacy_user_dir is None  # 自定义目录不做旧数据导入


def test_paths_accept_plain_strings(tmp_path):
    paths = StudioPaths(user=str(tmp_path / "data"), builtin=str(tmp_path / "builtin"))
    assert paths.settings_file == tmp_path / "data" / "config" / "ai_config.yaml"
    assert paths.builtin_presets_dir == tmp_path / "builtin" / "presets"
    assert Studio(paths).presets.list_all() == []


def test_source_checkout_defaults_to_repo_data_dir(monkeypatch):
    monkeypatch.delenv(paths_module.HOME_ENV, raising=False)
    assert paths_module.source_checkout_root() == ROOT
    paths = StudioPaths.default()
    assert paths.user == ROOT / "data"
    assert paths.builtin == BUILTIN
    assert paths.legacy_user_dir == ROOT / "src"


def test_frozen_build_keeps_data_next_to_the_executable(monkeypatch, tmp_path):
    monkeypatch.delenv(paths_module.HOME_ENV, raising=False)
    monkeypatch.setattr(paths_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths_module.sys, "executable", str(tmp_path / "app" / "studio.exe"))
    assert paths_module.default_user_dir() == tmp_path / "app"


def test_legacy_import_copies_once_and_never_overwrites(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    legacy = repo / "src"
    (legacy / "config").mkdir(parents=True)
    (legacy / "presets" / "categories" / "basic").mkdir(parents=True)
    (legacy / "config" / "ai_config.yaml").write_text("api_key: old\n", encoding="utf-8")
    (legacy / "presets" / "我的.json").write_text("{}", encoding="utf-8")
    (legacy / "presets" / "categories" / "basic" / "基础.json").write_text("{}", encoding="utf-8")

    paths = StudioPaths(user=repo / "data", builtin=tmp_path / "builtin")
    monkeypatch.setattr(StudioPaths, "legacy_user_dir", property(lambda self: legacy))

    copied = import_legacy_user_data(paths)
    assert len(copied) == 3
    assert paths.settings_file.read_text(encoding="utf-8") == "api_key: old\n"
    assert (paths.presets_dir / "categories" / "basic" / "基础.json").exists()

    paths.settings_file.write_text("api_key: new\n", encoding="utf-8")
    assert import_legacy_user_data(paths) == []
    assert paths.settings_file.read_text(encoding="utf-8") == "api_key: new\n"
    # 导入的旧扁平配置能被直接读懂
    assert Studio(paths).chat_settings().api_key == "new"


def test_studio_with_explicit_paths_never_imports_legacy_data(tmp_path):
    """测试 / 插件传入自己的目录时，不能把开发机上的真实密钥带进来。"""
    studio = Studio(StudioPaths(user=tmp_path / "data", builtin=tmp_path / "builtin"))
    assert studio.chat_settings().api_key == ""
    assert studio.presets.list_all() == []
    assert not studio.paths.settings_file.exists()
