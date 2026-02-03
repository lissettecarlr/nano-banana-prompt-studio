"""Web版本启动脚本"""
import subprocess
import sys
from pathlib import Path

def main():
    """启动Web服务器"""
    # 获取当前目录
    current_dir = Path(__file__).parent
    
    print("=" * 60)
    print("Nano Banana Prompt Tool - Web版本启动脚本")
    print("=" * 60)
    
    # 检查是否安装了依赖
    requirements_file = current_dir / "requirements.txt"
    if requirements_file.exists():
        print("\n正在检查依赖...")
        try:
            import flask
            import flask_cors
            import yaml
            import openai
            print("✓ 所有依赖已安装")
        except ImportError as e:
            print(f"✗ 缺少依赖: {e}")
            print("\n正在安装依赖...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
    
    # 启动Flask应用
    print("\n启动Web服务器...")
    app_file = current_dir / "app.py"
    subprocess.run([sys.executable, str(app_file)])

if __name__ == "__main__":
    main()
