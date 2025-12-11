"""AI 提示词生成服务 - 使用 OpenAI SDK（流式输出）"""
import json
import base64
from typing import Callable, Optional, List
from PyQt6.QtCore import QThread, pyqtSignal

from utils.ai_config import AIConfigManager


# 系统提示词，指导AI生成符合格式的提示词
SYSTEM_PROMPT = """你是一个专业的AI绘画提示词生成助手。用户会描述他们想要的画面，或者提供参考图片，你需要根据描述和图片内容生成一个结构化的JSON提示词。

如果用户提供了参考图片，请仔细分析图片中的：
- 角色特征（外貌、服装、配饰等）
- 场景环境（地点、光线、天气等）
- 画面风格（画风、色彩、质感等）
- 构图和镜头角度

然后结合用户的文字描述（如果有），生成符合图片风格和内容的提示词。

请严格按照以下JSON格式输出，不要输出任何其他内容,禁止用```JSON```包裹：

{
  "风格模式": "高保真二次元插画, 官方立绘风格, 赛璐璐上色",
  "画面气质": "清透, 治愈, 空灵, 极致可爱, 梦幻",
  "相机": {
    "机位角度": "微微仰视或平视视角",
    "构图": "全身中景，完整显示角色的身体，特别是脚部，强调人物与背景的互动",
    "镜头特性": "虚拟35mm镜头感",
    "传感器画质": "8K 超高清分辨率, 矢量级清晰度, 无噪点"
  },
  "场景": {
    "环境": {
      "地点设定": "蔚蓝档案风格的木质海边车站，背景是明亮的蓝天和巨大的积雨云",
      "光线": "高调摄影风格（High-key lighting），明亮的日光，强烈的环境光，没有死黑阴影",
      "天气氛围": "盛夏的晴朗午后，海风吹拂，空气中充满透明感"
    },
    "主体": {
      "整体描述": "蔚蓝档案的角色小鸟游星野（Takanashi Hoshino），二次元美少女",
      "外形特征": {
        "身材": "娇小可爱，萝莉体型",
        "面部": "圆润可爱的脸庞，带着标志性的慵懒神情，异色瞳（左蓝右橙）",
        "头发": "粉色长发，发梢微卷，头顶有标志性的粉色光环（Halo）和呆毛",
        "眼睛": "如宝石般闪亮通透的异色瞳孔，眼神清澈"
      },
      "表情与动作": {
        "情绪": "开心，放松，充满好奇",
        "动作": "坐在车站的木质长椅上，双腿悬空轻轻晃动，身体前倾，一只手放在椅子上撑着身体，另一只手在逗弄漂浮的蓝色小鲸鱼玩偶"
      },
      "服装": {
        "穿着": "严格参考输入图片的蓝白配色国风",
        "细节": "丝绸质感的宽大袖子，精致的腰封，飘动的丝带，可爱的绳结装饰"
      },
      "配饰": "头顶的兔子发饰，漂浮的蓝色鲸鱼玩偶"
    },
    "背景": {
      "描述": "背景是高饱和度的蓝天、白云和波光粼粼的大海，画面极其干净",
      "景深": "适度的景深虚化，让背景的云朵和大海成为清新的衬托"
    }
  },
  "审美控制": {
    "呈现意图": "顶级二次元游戏CG，Pixiv高赞插画，清新的壁纸风格",
    "材质真实度": [
      "二次元赛璐璐风格的皮肤质感，白皙透红",
      "头发具有光泽感和丝滑感",
      "衣物布料呈现清晰的褶皱和飘逸感，非写实材质"
    ],
    "色彩风格": {
      "整体色调": "清新的蓝白色调，粉色点缀，高亮度，低对比度",
      "对比度": "柔和的明暗过渡，拒绝油腻的厚涂感，保持画面通透",
      "特殊效果": "梦幻的粒子浮动，发光的线条"
    }
  }
}

注意事项：
1. 只输出JSON，不要有任何解释或markdown代码块标记
2. 所有字段都要填写，内容要简洁清楚，示例只是格式参考，不要完全照风格。
3. 如果用户描述的不是人物，外形特征相关字段可以适当调整描述
4. 生成的提示词要有画面感，用词要专业、优美
5. 格式要完整按照示例实现，不要遗漏任何字段"""

# 修改提示词的系统提示
MODIFY_SYSTEM_PROMPT = """你是一个专业的AI绘画提示词修改助手。用户会提供一个当前的JSON格式提示词和修改要求，可能还会提供参考图片，你需要根据修改要求和参考图片对当前提示词进行调整并返回修改后的JSON。

如果用户提供了参考图片，请仔细分析图片中的：
- 角色特征（外貌、服装、配饰等）
- 场景环境（地点、光线、天气等）
- 画面风格（画风、色彩、质感等）
- 构图和镜头角度

然后结合用户的文字修改要求，对提示词进行相应调整。

请严格按照以下要求操作：
1. 仔细分析用户当前的提示词结构和内容
2. 根据用户的修改要求和参考图片（如果有），针对性地调整相应字段
3. 保持原有的JSON结构不变，只修改相关内容
4. 确保修改后的内容仍然完整和合理
5. 只输出修改后的JSON，不要有任何解释或其他内容，禁止用```JSON```包裹

示例：
当前提示词：
{
  "风格模式": "高保真二次元插画, 官方立绘风格, 赛璐璐上色",
  "画面气质": "清透, 治愈, 空灵, 极致可爱, 梦幻",
  // ... 其他字段
}

用户要求："把场景改成雪景，人物穿冬装"

修改后：
{
  "风格模式": "高保真二次元插画, 官方立绘风格, 赛璐璐上色",
  "画面气质": "清透, 治愈, 空灵, 极致可爱, 梦幻",
  // ... 其他字段，但场景相关的字段被修改为雪景和冬装
}

"""

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