"""PyInstaller 入口脚本（build.py 使用）。

放在包外面是有意的：PyInstaller 会把入口脚本所在目录加进模块搜索路径，
如果直接用 src/nano_banana/desktop/main.py，desktop/ 下的模块会被当成顶层模块重复打包。
"""
from nano_banana.desktop.main import main

if __name__ == "__main__":
    main()
