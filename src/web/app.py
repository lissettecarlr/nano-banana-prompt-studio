"""Web版本的Flask后端服务器"""
import sys
import os
from pathlib import Path

# 添加父目录到路径，以便导入utils模块
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(src_dir))

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import json
import base64
from typing import Optional, List

from utils.yaml_handler import YamlHandler
from utils.preset_manager import PresetManager
from utils.ai_config import AIConfigManager
from components.gemini_client import GeminiClient


app = Flask(__name__, static_folder='static')
CORS(app)

# 初始化管理器
yaml_handler = YamlHandler()
preset_manager = PresetManager()
config_manager = AIConfigManager()


@app.route('/')
def index():
    """返回主页"""
    return send_from_directory('static', 'index.html')


@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools():
    """处理Chrome DevTools请求，防止404日志"""
    return jsonify({})


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取AI配置"""
    try:
        config = config_manager.load_config()
        # 隐藏敏感信息
        safe_config = {
            'base_url': config.get('base_url', ''),
            'model': config.get('model', ''),
            'gemini_base_url': config.get('gemini_base_url', ''),
            'gemini_model': config.get('gemini_model', ''),
            'has_api_key': bool(config.get('api_key')),
            'has_gemini_api_key': bool(config.get('gemini_api_key'))
        }
        return jsonify(safe_config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """更新AI配置"""
    try:
        data = request.json
        config = config_manager.load_config()
        
        # 更新配置
        if 'base_url' in data:
            config['base_url'] = data['base_url']
        if 'api_key' in data:
            config['api_key'] = data['api_key']
        if 'model' in data:
            config['model'] = data['model']
        if 'gemini_base_url' in data:
            config['gemini_base_url'] = data['gemini_base_url']
        if 'gemini_api_key' in data:
            config['gemini_api_key'] = data['gemini_api_key']
        if 'gemini_model' in data:
            config['gemini_model'] = data['gemini_model']
        
        config_manager.save_config(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/options', methods=['GET'])
def get_options():
    """获取所有字段选项"""
    try:
        options = yaml_handler.load_options()
        return jsonify(options)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/options/<field_name>', methods=['GET'])
def get_field_options(field_name):
    """获取指定字段的选项"""
    try:
        options = yaml_handler.get_field_options(field_name)
        return jsonify(options)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/options/<field_name>', methods=['POST'])
def add_option(field_name):
    """添加选项"""
    try:
        data = request.json
        value = data.get('value')
        if value:
            yaml_handler.add_option(field_name, value)
            return jsonify({'success': True})
        return jsonify({'error': '值不能为空'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """获取所有预设"""
    try:
        presets = preset_manager.get_all_presets()
        # 转换datetime为字符串
        for preset in presets:
            preset['modified_time'] = preset['modified_time'].isoformat()
        return jsonify(presets)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/presets/<name>', methods=['GET'])
def get_preset(name):
    """获取指定预设"""
    try:
        preset = preset_manager.load_preset(name)
        if preset:
            return jsonify(preset)
        return jsonify({'error': '预设不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/presets', methods=['POST'])
def save_preset():
    """保存预设"""
    try:
        data = request.json
        name = data.get('name')
        preset_data = data.get('data')
        
        if not name or not preset_data:
            return jsonify({'error': '名称和数据不能为空'}), 400
        
        success = preset_manager.save_preset(name, preset_data)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': '保存失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/presets/<name>', methods=['DELETE'])
def delete_preset(name):
    """删除预设"""
    try:
        success = preset_manager.delete_preset(name)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': '删除失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def generate_prompt():
    """生成提示词（流式）"""
    try:
        data = request.json
        user_prompt = data.get('prompt', '')
        images = data.get('images', [])  # base64编码的图片列表
        
        if not user_prompt and not images:
            return jsonify({'error': '请提供文字描述或参考图片'}), 400
        
        # 导入AI服务
        from openai import OpenAI
        import httpx
        
        config = config_manager.load_config()
        base_url = config.get('base_url', '').rstrip('/')
        api_key = config.get('api_key', '')
        model = config.get('model', 'gpt-4o-mini')
        
        if not api_key:
            return jsonify({'error': '请先配置API密钥'}), 400
        
        # 创建客户端
        http_client = httpx.Client(http2=False)
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=180,
            http_client=http_client,
        )
        
        # 构建消息
        user_content = []
        
        # 添加图片
        if images:
            for img_data in images:
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": img_data  # 已经是data:image/...;base64,xxx格式
                    }
                })
        
        # 添加文本
        if user_prompt:
            if user_content:
                user_content.append({
                    "type": "text",
                    "text": f"请根据以下描述和参考图片生成提示词：\n\n{user_prompt}"
                })
            else:
                user_content = f"请根据以下描述生成提示词：\n\n{user_prompt}"
        elif user_content:
            user_content.append({
                "type": "text",
                "text": "请根据参考图片生成提示词。"
            })
        
        # 系统提示词
        from utils.ai_service import SYSTEM_PROMPT
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
        
        # 流式生成
        def generate():
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                )
                
                for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            # 发送SSE格式的数据
                            yield f"data: {json.dumps({'content': delta.content})}\n\n"
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """生成图片"""
    temp_files = []
    try:
        data = request.json
        prompt = data.get('prompt', '')
        images = data.get('images', [])
        aspect_ratio = data.get('aspect_ratio', '1:1')
        image_size = data.get('image_size', '2K') # GeminiClient default is 2K
        thinking_level = data.get('thinking_level', 'low')

        if not prompt:
            return jsonify({'error': '提示词不能为空'}), 400

        # 处理图片数据：如果是Data URI，转为临时文件
        import tempfile
        processed_images = []
        if images:
            for img_str in images:
                if isinstance(img_str, str) and img_str.startswith('data:'):
                    try:
                        # 解析Data URI: data:image/png;base64,xxxx
                        header, encoded = img_str.split(';base64,')
                        mime_type = header.split(':')[1]
                        
                        # 确定扩展名
                        ext_map = {
                            'image/jpeg': '.jpg',
                            'image/png': '.png',
                            'image/webp': '.webp',
                            'image/gif': '.gif',
                            'image/bmp': '.bmp'
                        }
                        ext = ext_map.get(mime_type, '.jpg')
                        
                        # 解码并保存到临时文件
                        img_data = base64.b64decode(encoded)
                        fd, path = tempfile.mkstemp(suffix=ext)
                        with os.fdopen(fd, 'wb') as f:
                            f.write(img_data)
                        
                        temp_files.append(path)
                        processed_images.append(path)
                    except Exception as e:
                        print(f"Error processing image: {e}")
                        # 如果解析失败，尝试原样传递（虽然可能也会失败）
                        processed_images.append(img_str)
                else:
                    processed_images.append(img_str)

        # 获取配置
        config = config_manager.get_gemini_config()
        base_url = config.get('base_url', '')
        api_key = config.get('api_key', '')
        model = config.get('model', 'gemini-3-pro-image-preview')

        if not base_url or not api_key:
            return jsonify({'error': '请先配置Gemini API'}), 400

        # 初始化客户端
        client = GeminiClient(
            base_url=base_url,
            api_key=api_key,
            image_model=model
        )
        
        client.set_aspect_ratio(aspect_ratio)
        client.set_image_size(image_size)
        client.set_thinking_level(thinking_level)

        # 生成图片
        generated_image = client.generate_image(
            text=prompt,
            images=processed_images if processed_images else None
        )

        if generated_image:
            # 转为base64返回
            from io import BytesIO
            buffered = BytesIO()
            generated_image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return jsonify({'image': f"data:image/png;base64,{img_str}"})
        else:
            return jsonify({'error': '生成图片失败，未返回图片数据'}), 500

    except Exception as e:
        print(f"Generate Image Error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        # 清理临时文件
        for path in temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Error removing temp file {path}: {e}")


@app.route('/api/modify', methods=['POST'])

def modify_prompt():
    """修改提示词（流式）"""
    try:
        data = request.json
        current_data = data.get('current_data', '')
        modify_request = data.get('modify_request', '')
        images = data.get('images', [])
        
        if not current_data or not modify_request:
            return jsonify({'error': '当前数据和修改要求不能为空'}), 400
        
        # 导入AI服务
        from openai import OpenAI
        import httpx
        
        config = config_manager.load_config()
        base_url = config.get('base_url', '').rstrip('/')
        api_key = config.get('api_key', '')
        model = config.get('model', 'gpt-4o-mini')
        
        if not api_key:
            return jsonify({'error': '请先配置API密钥'}), 400
        
        # 创建客户端
        http_client = httpx.Client(http2=False)
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=180,
            http_client=http_client,
        )
        
        # 构建消息
        user_content = []
        
        # 添加图片
        if images:
            for img_data in images:
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": img_data
                    }
                })
        
        # 添加文本
        text_content = f"当前提示词：\n{current_data}\n\n修改要求：{modify_request}\n\n请返回修改后的JSON提示词:"
        
        if user_content:
            user_content.append({
                "type": "text",
                "text": text_content
            })
            user_message_content = user_content
        else:
            user_message_content = text_content
        
        # 系统提示词
        from utils.ai_service import MODIFY_SYSTEM_PROMPT
        
        messages = [
            {"role": "system", "content": MODIFY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message_content}
        ]
        
        # 流式生成
        def generate():
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                )
                
                for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            yield f"data: {json.dumps({'content': delta.content})}\n\n"
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # 确保static目录存在
    static_dir = current_dir / 'static'
    static_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("Nano Banana Prompt Tool - Web版本")
    print("=" * 60)
    print(f"服务器启动在: http://localhost:5000")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
