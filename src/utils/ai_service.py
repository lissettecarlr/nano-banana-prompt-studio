"""AI 提示词生成服务 - 使用 OpenAI SDK（流式输出）"""
import json
import base64
from typing import Callable, Optional, List
from PyQt6.QtCore import QThread, pyqtSignal

from utils.ai_config import AIConfigManager
from utils.ai_prompts import SYSTEM_PROMPT, MODIFY_SYSTEM_PROMPT


class AIGenerateThread(QThread):
    """AI生成线程 - 流式输出"""
    
    # 信号
    finished = pyqtSignal(dict)      # 成功时发送生成的数据
    error = pyqtSignal(str)          # 错误时发送错误信息
    progress = pyqtSignal(str)       # 进度信息
    stream_chunk = pyqtSignal(str)   # 流式内容块
    stream_done = pyqtSignal(str)    # 流式完成，发送完整内容
    
    def __init__(self, user_prompt: str, config_manager: AIConfigManager, image_paths: Optional[List[str]] = None):
        super().__init__()
        self.user_prompt = user_prompt
        self.config_manager = config_manager
        self.image_paths = image_paths or []
        self._cancelled = False
    
    def _encode_image(self, image_path: str) -> str:
        """将图片编码为base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"读取图片失败 {image_path}: {str(e)}")
    
    def _get_image_mime_type(self, image_path: str) -> str:
        """根据文件扩展名获取MIME类型"""
        ext = image_path.lower().split('.')[-1]
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'webp': 'image/webp',
            'bmp': 'image/bmp',
        }
        return mime_types.get(ext, 'image/png')
    
    def cancel(self):
        """取消生成"""
        self._cancelled = True
    
    def run(self):
        try:
            self.progress.emit("正在连接AI服务...")
            
            config = self.config_manager.load_config()
            base_url = config.get("base_url", "").rstrip("/")
            api_key = config.get("api_key", "")
            model = config.get("model", "gpt-4o-mini")
            
            if not api_key:
                self.error.emit("请先配置API密钥")
                return
            
            # 延迟导入
            try:
                from openai import OpenAI
            except ImportError as e:
                self.error.emit(f"openai 导入失败: {e}")
                return
            except Exception as e:
                self.error.emit(f"openai 加载异常: {type(e).__name__}: {e}")
                return
            
            # 创建客户端（禁用 http2 避免 cffi/pycparser 问题）
            import httpx
            http_client = httpx.Client(http2=False)
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=180,
                http_client=http_client,
            )
            
            self.progress.emit("正在生成提示词...")
            
            # 构建消息
            user_content = []
            
            # 如果有图片，添加图片到消息中
            if self.image_paths:
                for image_path in self.image_paths:
                    try:
                        base64_image = self._encode_image(image_path)
                        mime_type = self._get_image_mime_type(image_path)
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        })
                    except Exception as e:
                        self.error.emit(f"处理图片失败: {str(e)}")
                        return
            
            # 添加文本内容
            if self.user_prompt:
                if user_content:
                    # 有图片和文本
                    user_content.append({
                        "type": "text",
                        "text": f"请根据以下描述和参考图片生成提示词：\n\n{self.user_prompt}"
                    })
                else:
                    # 只有文本，没有图片
                    user_content = f"请根据以下描述生成提示词：\n\n{self.user_prompt}"
            elif user_content:
                # 只有图片没有文本
                user_content.append({
                    "type": "text",
                    "text": "请根据参考图片生成提示词。"
                })
            else:
                self.error.emit("请提供文字描述或参考图片")
                return
            
            # 构建消息
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ]
            
            # 流式调用API
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                )
                
                full_content = ""
                for chunk in stream:
                    if self._cancelled:
                        self.progress.emit("已取消")
                        return
                    
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            content_piece = delta.content
                            full_content += content_piece
                            # 发送流式块
                            self.stream_chunk.emit(content_piece)
                
                # 流式完成
                self.stream_done.emit(full_content)
                
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    self.error.emit("API密钥无效或已过期，请检查配置")
                elif "429" in error_msg or "rate" in error_msg.lower():
                    self.error.emit("请求过于频繁，请稍后再试")
                elif "timeout" in error_msg.lower():
                    self.error.emit("请求超时，请检查网络连接或稍后再试")
                elif "connect" in error_msg.lower():
                    self.error.emit(f"网络连接失败: {error_msg}")
                else:
                    self.error.emit(f"API调用失败: {error_msg}")
                return
                
        except Exception as e:
            import traceback
            self.error.emit(f"发生未知错误: {str(e)}\n{traceback.format_exc()}")


class AIModifyThread(QThread):
    """AI修改线程 - 流式输出"""
    
    # 信号
    finished = pyqtSignal(dict)      # 成功时发送生成的数据
    error = pyqtSignal(str)          # 错误时发送错误信息
    progress = pyqtSignal(str)       # 进度信息
    stream_chunk = pyqtSignal(str)   # 流式内容块
    stream_done = pyqtSignal(str)    # 流式完成，发送完整内容
    
    def __init__(self, current_data: str, modify_request: str, config_manager: AIConfigManager, image_paths: Optional[List[str]] = None):
        super().__init__()
        self.current_data = current_data
        self.modify_request = modify_request
        self.config_manager = config_manager
        self.image_paths = image_paths or []
        self._cancelled = False
    
    def _encode_image(self, image_path: str) -> str:
        """将图片编码为base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"读取图片失败 {image_path}: {str(e)}")
    
    def _get_image_mime_type(self, image_path: str) -> str:
        """根据文件扩展名获取MIME类型"""
        ext = image_path.lower().split('.')[-1]
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'webp': 'image/webp',
            'bmp': 'image/bmp',
        }
        return mime_types.get(ext, 'image/png')
    
    def cancel(self):
        """取消生成"""
        self._cancelled = True
    
    def run(self):
        try:
            self.progress.emit("正在连接AI服务...")
            
            config = self.config_manager.load_config()
            base_url = config.get("base_url", "").rstrip("/")
            api_key = config.get("api_key", "")
            model = config.get("model", "")
            
            if not api_key:
                self.error.emit("请先配置API密钥")
                return
            
            if not base_url:
                self.error.emit("请先配置Base URL")
                return
            
            if not model:
                self.error.emit("请先配置模型名称")
                return
            
            # 延迟导入
            try:
                from openai import OpenAI
            except ImportError as e:
                self.error.emit(f"openai 导入失败: {e}")
                return
            except Exception as e:
                self.error.emit(f"openai 加载异常: {type(e).__name__}: {e}")
                return
            
            # 创建客户端（禁用 http2 避免 cffi/pycparser 问题）
            import httpx
            http_client = httpx.Client(http2=False)
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=180,
                http_client=http_client,
            )
            
            self.progress.emit("正在修改提示词...")
            
            # 构建消息
            user_content = []
            
            # 如果有图片，添加图片到消息中
            if self.image_paths:
                for image_path in self.image_paths:
                    try:
                        base64_image = self._encode_image(image_path)
                        mime_type = self._get_image_mime_type(image_path)
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        })
                    except Exception as e:
                        self.error.emit(f"处理图片失败: {str(e)}")
                        return
            
            # 添加文本内容
            text_content = f"当前提示词：\n{self.current_data}\n\n修改要求：{self.modify_request}\n\n请返回修改后的JSON提示词:"
            
            if user_content:
                # 有图片，使用多模态格式
                user_content.append({
                    "type": "text",
                    "text": text_content
                })
                user_message_content = user_content
            else:
                # 只有文本
                user_message_content = text_content
            
            messages = [
                {"role": "system", "content": MODIFY_SYSTEM_PROMPT},
                {"role": "user", "content": user_message_content}
            ]
            
            # 流式调用API
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                )
                
                full_content = ""
                for chunk in stream:
                    if self._cancelled:
                        self.progress.emit("已取消")
                        return
                    
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            content_piece = delta.content
                            full_content += content_piece
                            # 发送流式块
                            self.stream_chunk.emit(content_piece)
                
                # 流式完成
                self.stream_done.emit(full_content)
                
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    self.error.emit("API密钥无效或已过期，请检查配置")
                elif "429" in error_msg or "rate" in error_msg.lower():
                    self.error.emit("请求过于频繁，请稍后再试")
                elif "timeout" in error_msg.lower():
                    self.error.emit("请求超时，请检查网络连接或稍后再试")
                elif "connect" in error_msg.lower():
                    self.error.emit(f"网络连接失败: {error_msg}")
                else:
                    self.error.emit(f"API调用失败: {error_msg}")
                return
                
        except Exception as e:
            import traceback
            self.error.emit(f"发生未知错误: {str(e)}\n{traceback.format_exc()}")


class AIService:
    """AI服务封装类"""
    
    def __init__(self):
        self.config_manager = AIConfigManager()
        self._current_thread: Optional[AIGenerateThread] = None
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return self.config_manager.is_configured()
    
    def generate_async(
        self,
        user_prompt: str,
        on_finished: Callable[[dict], None],
        on_error: Callable[[str], None],
        on_progress: Callable[[str], None] = None,
        on_stream_chunk: Callable[[str], None] = None,
        on_stream_done: Callable[[str], None] = None,
        image_paths: Optional[List[str]] = None,
    ) -> AIGenerateThread:
        """
        异步流式生成提示词
        
        :param user_prompt: 用户输入的画面描述
        :param on_finished: 成功回调（JSON解析后），参数为生成的数据字典
        :param on_error: 错误回调，参数为错误信息
        :param on_progress: 进度回调，参数为进度信息
        :param on_stream_chunk: 流式内容块回调
        :param on_stream_done: 流式完成回调，参数为完整文本
        :param image_paths: 参考图片路径列表（可选）
        :return: 线程对象
        """
        # 如果有正在运行的线程，先停止
        if self._current_thread and self._current_thread.isRunning():
            self._current_thread.cancel()
            self._current_thread.wait(1000)
        
        thread = AIGenerateThread(user_prompt, self.config_manager, image_paths)
        thread.finished.connect(on_finished)
        thread.error.connect(on_error)
        if on_progress:
            thread.progress.connect(on_progress)
        if on_stream_chunk:
            thread.stream_chunk.connect(on_stream_chunk)
        if on_stream_done:
            thread.stream_done.connect(on_stream_done)
        
        self._current_thread = thread
        thread.start()
        return thread
    
    def generate_modify_async(
        self,
        current_data: str,
        modify_request: str,
        on_finished: Callable[[dict], None],
        on_error: Callable[[str], None],
        on_progress: Callable[[str], None] = None,
        on_stream_chunk: Callable[[str], None] = None,
        on_stream_done: Callable[[str], None] = None,
        image_paths: Optional[List[str]] = None,
    ) -> AIModifyThread:
        """
        异步流式修改提示词
        
        :param current_data: 当前提示词的JSON字符串
        :param modify_request: 用户的修改要求
        :param on_finished: 成功回调（JSON解析后），参数为生成的数据字典
        :param on_error: 错误回调，参数为错误信息
        :param on_progress: 进度回调，参数为进度信息
        :param on_stream_chunk: 流式内容块回调
        :param on_stream_done: 流式完成回调，参数为完整文本
        :param image_paths: 参考图片路径列表（可选）
        :return: 线程对象
        """
        # 如果有正在运行的线程，先停止
        if self._current_thread and self._current_thread.isRunning():
            self._current_thread.cancel()
            self._current_thread.wait(1000)
        
        thread = AIModifyThread(current_data, modify_request, self.config_manager, image_paths)
        thread.finished.connect(on_finished)
        thread.error.connect(on_error)
        if on_progress:
            thread.progress.connect(on_progress)
        if on_stream_chunk:
            thread.stream_chunk.connect(on_stream_chunk)
        if on_stream_done:
            thread.stream_done.connect(on_stream_done)
        
        self._current_thread = thread
        thread.start()
        return thread
    
    def cancel(self):
        """取消当前生成"""
        if self._current_thread and self._current_thread.isRunning():
            self._current_thread.cancel()
            self._current_thread.wait(1000)