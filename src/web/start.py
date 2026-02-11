"""改进的Web服务器启动脚本 - 自动打开浏览器"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
import threading

def check_dependencies():
    """检查并安装依赖"""
    current_dir = Path(__file__).parent
    requirements_file = current_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print("警告: requirements.txt 文件不存在")
        return
    
    print("正在检查依赖...")
    try:
        import flask
        import flask_cors
        import yaml
        import openai
        import httpx
        from google import genai
        print("✓ 所有依赖已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("\n正在安装依赖...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                check=True
            )
            print("✓ 依赖安装完成")
            return True
        except subprocess.CalledProcessError:
            print("✗ 依赖安装失败")
            return False

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)  # 等待服务器启动
    url = "http://localhost:5000"
    print(f"\n正在打开浏览器: {url}")
    webbrowser.open(url)

def main():
    """启动Web服务器"""
    print("=" * 60)
    print("Nano Banana Prompt Tool - Web版本")
    print("=" * 60)
    print()
    
    # 检查依赖
    if not check_dependencies():
        print("\n依赖安装失败，请手动安装后重试")
        input("按回车键退出...")
        return
    
    # 启动浏览器（在后台线程）
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # 启动Flask应用
    print("\n正在启动Web服务器...")
    print("=" * 60)
    
    current_dir = Path(__file__).parent
    app_file = current_dir / "app.py"
    
    try:
        subprocess.run([sys.executable, str(app_file)])
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main()
