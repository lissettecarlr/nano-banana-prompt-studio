"""
Nano Banana 图片生成工具 - 打包脚本
将应用打包成独立的可执行文件

使用方法:
    python build.py
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path


APP_NAME = 'NanoBananaPromptStudio'


def clean_build_dirs():
    """清理之前的构建目录"""
    dirs_to_clean = ['build', 'dist', 'output']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)


def clean_temp_files():
    """清理打包产生的临时文件"""
    print("\n清理临时文件...")
    
    # 删除 build 和 dist 目录
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  已删除: {dir_name}/")
    
    # 删除 .spec 文件
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"  已删除: {spec_file}")


def install_pyinstaller():
    """确保 PyInstaller 已安装"""
    try:
        import PyInstaller
        print(f"PyInstaller 已安装: {PyInstaller.__version__}")
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])


def build_exe():
    """使用 PyInstaller 构建可执行文件"""
    print("\n开始构建可执行文件...")
    
    # PyInstaller 参数
    pyinstaller_args = [
        'src/main.py',                          # 入口文件
        f'--name={APP_NAME}',                   # 生成的exe名称
        '--windowed',                            # 无控制台窗口 (GUI应用)
        '--onedir',                              # 打包成目录形式 (比单文件更快启动)
        '--noconfirm',                           # 不确认覆盖
        '--clean',                               # 清理临时文件
        '--icon=images/logo.png',               # 应用图标
        
        # 添加数据文件（注意：不要打包 ai_config.yaml，里面有密钥）
        f'--add-data=src/config/options.yaml{os.pathsep}config',  # 只打包 options.yaml
        f'--add-data=src/presets{os.pathsep}presets',             # 预设目录
        f'--add-data=images/logo.png{os.pathsep}images',          # logo图片
        
        # 隐藏导入（确保所有模块都被包含）
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=yaml',
        '--hidden-import=pyperclip',
        '--hidden-import=PIL.Image',
        '--hidden-import=openai',                     # AI 服务
        '--hidden-import=openai.resources',
        '--hidden-import=openai.resources.chat',
        '--hidden-import=openai.resources.chat.completions',
        '--hidden-import=openai._streaming',
        '--hidden-import=httpx',
        '--hidden-import=httpcore',
        '--hidden-import=h11',
        '--hidden-import=anyio',
        '--hidden-import=sniffio',
        '--hidden-import=certifi',
        '--hidden-import=pydantic',
        '--hidden-import=pydantic_core',
        '--hidden-import=jiter',
        '--hidden-import=jaraco.text',                # pkg_resources 依赖
        '--hidden-import=jaraco.functools',
        '--hidden-import=jaraco.context',
        '--collect-all=jaraco',
        '--collect-all=jaraco.text',
        '--collect-all=jaraco.functools',
        '--collect-all=jaraco.context',
        '--collect-all=more_itertools',
        '--collect-all=backports',
        '--collect-all=backports.tarfile',
        
        # 收集整个 openai 包及其关键依赖
        '--collect-all=openai',
        '--collect-all=httpx',
        '--collect-all=httpcore',
        '--collect-all=pydantic',
        '--collect-all=pydantic_core',
        '--collect-all=jiter',
        '--collect-all=anyio',
        '--collect-all=sniffio',
        '--collect-all=certifi',
        '--collect-all=h11',
        '--collect-all=typing_extensions',
        '--collect-all=distro',
        '--collect-all=PIL',
        # 排除 http2 相关（避免 cffi/pycparser 问题）
        '--exclude-module=h2',
        '--exclude-module=hpack',
        '--exclude-module=hyperframe',
        '--exclude-module=cffi',
        '--exclude-module=pycparser',
        
        # 排除冲突的 Qt 绑定
        '--exclude-module=PyQt5',
        '--exclude-module=PySide6',
        '--exclude-module=PySide2',
        
        # 排除不需要的大型库（可能被环境中其他包间接引入）
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        '--exclude-module=torch',
        '--exclude-module=tensorflow',
        '--exclude-module=cv2',
        '--exclude-module=sklearn',
        '--exclude-module=IPython',
        '--exclude-module=jupyter',
        '--exclude-module=notebook',
        '--exclude-module=pytest',
        # '--exclude-module=setuptools',  # pkg_resources 需要，不能排除
        '--exclude-module=pip',
        '--exclude-module=sounddevice',
        '--exclude-module=soundfile',
        
        # 优化
        '--optimize=2',                          # Python优化级别
        
        # 排除不需要的 Qt 模块（减小体积）
        # '--exclude-module=PyQt6.QtNetwork',  # AI功能可能需要网络模块
        '--exclude-module=PyQt6.QtPdf',
        '--exclude-module=PyQt6.QtSvg',
        '--exclude-module=PyQt6.QtQml',
        '--exclude-module=PyQt6.QtQuick',
        '--exclude-module=PyQt6.QtWebEngine',
        '--exclude-module=PyQt6.QtMultimedia',
        '--exclude-module=PyQt6.QtBluetooth',
        '--exclude-module=PyQt6.QtPositioning',
        '--exclude-module=PyQt6.QtSensors',
        '--exclude-module=PyQt6.QtSerialPort',
        '--exclude-module=PyQt6.QtSql',
        '--exclude-module=PyQt6.QtTest',
        '--exclude-module=PyQt6.QtXml',
    ]
    
    # 运行 PyInstaller
    subprocess.check_call([sys.executable, '-m', 'PyInstaller'] + pyinstaller_args)


def slim_output(output_dir: Path):
    """删除不必要的文件以减小体积"""
    print("\n精简输出目录...")
    
    removed_size = 0
    internal_dir = output_dir / '_internal'
    qt_dir = internal_dir / 'PyQt6' / 'Qt6'
    qt_bin = qt_dir / 'bin'
    qt_plugins = qt_dir / 'plugins'
    
    # === 删除大型不必要的 DLL ===
    
    if sys.platform == 'win32':
        # opengl32sw.dll - 软件 OpenGL 渲染，现代电脑都有硬件加速 (~20MB)
        opengl_sw = qt_bin / 'opengl32sw.dll'
        if opengl_sw.exists():
            removed_size += opengl_sw.stat().st_size
            opengl_sw.unlink()
            print(f"  已删除: opengl32sw.dll (软件渲染)")
    
    # libcrypto / libssl - AI功能需要HTTPS，保留这些库
    # for f in internal_dir.glob('libcrypto*.dll'):
    #     removed_size += f.stat().st_size
    #     f.unlink()
    #     print(f"  已删除: {f.name} (加密库)")
    # for f in internal_dir.glob('libssl*.dll'):
    #     removed_size += f.stat().st_size
    #     f.unlink()
    #     print(f"  已删除: {f.name} (SSL库)")
    
    # unicodedata.pyd - Unicode 数据库，openai/pydantic 需要，保留
    # unicodedata = internal_dir / 'unicodedata.pyd'
    # if unicodedata.exists():
    #     removed_size += unicodedata.stat().st_size
    #     unicodedata.unlink()
    #     print(f"  已删除: unicodedata.pyd")
    
    # === 删除 Qt 相关不必要文件 ===
    
    # Qt 翻译文件（不需要多语言）
    translations_dir = qt_dir / 'translations'
    if translations_dir.exists():
        for f in translations_dir.iterdir():
            removed_size += f.stat().st_size
        shutil.rmtree(translations_dir)
        print(f"  已删除: Qt 翻译文件")
    
    # 不需要的 Qt DLL（保留 Qt6Network.dll，AI功能需要）
    if sys.platform == 'win32':
        for dll_name in ['Qt6Pdf.dll', 'Qt6Svg.dll']:
            dll_path = qt_bin / dll_name
            if dll_path.exists():
                removed_size += dll_path.stat().st_size
                dll_path.unlink()
                print(f"  已删除: {dll_name}")
    
    # === 删除不需要的平台插件 ===
    
    platforms_dir = qt_plugins / 'platforms'
    if platforms_dir.exists() and sys.platform == 'win32':
        # 只保留 qwindows.dll，删除其他平台
        for f in platforms_dir.iterdir():
            if f.name not in {'qwindows.dll'}:
                removed_size += f.stat().st_size
                f.unlink()
                print(f"  已删除: platforms/{f.name}")
    
    # === 删除不需要的图像格式插件 ===
    
    imageformats_dir = qt_plugins / 'imageformats'
    if imageformats_dir.exists() and sys.platform == 'win32':
        keep_formats = {'qjpeg.dll', 'qico.dll', 'qgif.dll', 'qsvg.dll'}
        for f in imageformats_dir.iterdir():
            if f.name not in keep_formats:
                removed_size += f.stat().st_size
                f.unlink()
                print(f"  已删除: imageformats/{f.name}")
    
    # === 删除不需要的插件目录 ===
    
    # generic 插件（触摸屏相关）
    generic_dir = qt_plugins / 'generic'
    if generic_dir.exists():
        for f in generic_dir.iterdir():
            removed_size += f.stat().st_size
        shutil.rmtree(generic_dir)
        print(f"  已删除: generic 插件目录")
    
    # iconengines 插件（SVG 图标引擎）
    iconengines_dir = qt_plugins / 'iconengines'
    if iconengines_dir.exists():
        for f in iconengines_dir.iterdir():
            removed_size += f.stat().st_size
        shutil.rmtree(iconengines_dir)
        print(f"  已删除: iconengines 插件目录")
    
    # styles 插件（如果不需要 modern windows style）
    # styles_dir = qt_plugins / 'styles'
    # if styles_dir.exists():
    #     for f in styles_dir.iterdir():
    #         removed_size += f.stat().st_size
    #     shutil.rmtree(styles_dir)
    #     print(f"  已删除: styles 插件目录")
    



def create_output():
    """创建最终输出目录"""
    print("\n创建输出目录...")
    
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # 复制打包结果到 output
    dist_app = Path(f'dist/{APP_NAME}')
    if sys.platform == 'darwin':
        dist_app = Path(f'dist/{APP_NAME}.app')
        
    if dist_app.exists():
        # macOS .app 是一个文件夹，直接复制整个 .app
        if sys.platform == 'darwin':
            dest = output_dir / dist_app.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(dist_app, dest)
        else:
            # Windows/Linux 复制文件夹内的内容
            for item in dist_app.iterdir():
                dest = output_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
    
    # 确保 config 和 presets 目录存在且可写
    config_dir = output_dir / 'config'
    presets_dir = output_dir / 'presets'
    images_dir = output_dir / 'images'
    
    config_dir.mkdir(exist_ok=True)
    presets_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)
    
    # 复制配置文件（如果不存在）
    config_src = Path('src/config/options.yaml')
    config_dst = config_dir / 'options.yaml'
    if config_src.exists() and not config_dst.exists():
        shutil.copy2(config_src, config_dst)
    
    # 复制预设文件
    presets_src = Path('src/presets')
    if presets_src.exists():
        for preset_file in presets_src.glob('*.json'):
            shutil.copy2(preset_file, presets_dir / preset_file.name)
    
    # 复制 logo
    logo_src = Path('images/logo.png')
    logo_dst = images_dir / 'logo.png'
    if logo_src.exists():
        shutil.copy2(logo_src, logo_dst)
    
    # 精简输出
    slim_output(output_dir)
    
    print(f"\n打包完成！输出目录: {output_dir.absolute()}")
    print("\n目录结构:")
    print_tree(output_dir)


def print_tree(path: Path, prefix: str = ""):
    """打印目录树"""
    items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        print(f"{prefix}{current_prefix}{item.name}")
        if item.is_dir():
            next_prefix = "    " if is_last else "│   "
            # 限制深度，避免打印太多内容
            if prefix.count("│") < 2:
                print_tree(item, prefix + next_prefix)


def main():
    print("=" * 50)
    print("Nano Banana 生图工具 - 打包工具")
    print("=" * 50)
    
    # 确保在项目根目录运行
    if not os.path.exists('src/main.py'):
        print("错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    try:
        # 1. 清理旧构建
        clean_build_dirs()
        
        # 2. 安装 PyInstaller
        install_pyinstaller()
        
        # 3. 构建 exe
        build_exe()
        
        # 4. 创建最终输出
        create_output()
        
        # 5. 清理临时文件
        clean_temp_files()
        
        print("\n" + "=" * 50)
        print("🎉 打包成功！")
        print("=" * 50)
    
    except subprocess.CalledProcessError as e:
        print(f"\n构建失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

