"""
Gemini AI 客户端封装模块

功能说明：
    封装 Google Gemini API，提供文本对话和图片生成两种模式。

核心类：
    GeminiClient - Gemini客户端管理类

使用示例：
    from gemini_client import GeminiClient
    
    client = GeminiClient(base_url="https://xxx", api_key="sk-xxx")
    
    # 模式1: 文本对话（可带图片输入，返回文本）
    response = client.chat("描述这张图片", images=["photo.jpg"])
    print(response)  # 文本内容
    
    # 模式2: 图片生成（传入文本和可选图片，返回图片）
    image = client.generate_image("画一只柴犬")
    image.save("output.png")
    
    # 图片编辑
    image = client.generate_image("把水果换成香蕉", images=["input.jpg"])
    image.save("edited.png")
"""

import os
import base64
from io import BytesIO
from typing import List, Union, Optional, Tuple
from PIL import Image
from loguru import logger

from google import genai
from google.genai import types

os.environ['NO_PROXY'] = '*'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

ASPECT_RATIO_LIST = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
IMAGE_SIZE_LIST = ["1K", "2K", "4K"]
THINKING_LEVEL_LIST = ["none", "low", "medium", "high"]


class GeminiClient:
    """Gemini AI 客户端封装类"""
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        text_model: str = "gemini-3-pro-preview",
        image_model: str = "gemini-3-pro-image-preview"
    ):
        """
        初始化 Gemini 客户端
        
        Args:
            base_url: API 基础URL
            api_key: API 密钥
            text_model: 文本模型名称（用于对话，可识图）
            image_model: 图片生成模型名称
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.text_model = text_model
        self.image_model = image_model
        
        # 图片生成配置
        self.aspect_ratio = "1:1"
        self.image_size = "2K"
        self.thinking_level = "low"
        
        # 初始化客户端
        self.client = genai.Client(
            http_options=types.HttpOptions(base_url=self.base_url),
            api_key=self.api_key
        )
        
        logger.info(f"[GeminiClient] 初始化完成，API地址: {self.base_url}")
    
    def set_aspect_ratio(self, aspect_ratio: str) -> "GeminiClient":
        """设置图片宽高比"""
        if aspect_ratio not in ASPECT_RATIO_LIST:
            raise ValueError(f"宽高比不支持: {aspect_ratio}，可选: {ASPECT_RATIO_LIST}")
        self.aspect_ratio = aspect_ratio
        return self
    
    def set_image_size(self, image_size: str) -> "GeminiClient":
        """设置图片尺寸"""
        if image_size not in IMAGE_SIZE_LIST:
            raise ValueError(f"图片尺寸不支持: {image_size}，可选: {IMAGE_SIZE_LIST}")
        self.image_size = image_size
        return self
    
    def set_thinking_level(self, level: str) -> "GeminiClient":
        """设置思考级别"""
        if level not in THINKING_LEVEL_LIST:
            raise ValueError(f"思考级别不支持: {level}，可选: {THINKING_LEVEL_LIST}")
        self.thinking_level = level
        return self
    
    @staticmethod
    def _get_mime_type(file_path: str) -> str:
        """根据文件扩展名获取 MIME 类型"""
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }
        return mime_types.get(ext, 'image/jpeg')
    
    @staticmethod
    def _load_image_as_base64(image_path: str) -> Tuple[str, str]:
        """
        读取图片文件并转为 base64
        
        Returns:
            (mime_type, base64_data) 元组
        """
        mime_type = GeminiClient._get_mime_type(image_path)
        with open(image_path, 'rb') as f:
            base64_data = base64.b64encode(f.read()).decode('utf-8')
        return mime_type, base64_data
    
    def _build_parts(self, text: str, images: Optional[List[str]] = None) -> List[types.Part]:
        """
        构建请求的 parts 列表
        
        Args:
            text: 文本内容
            images: 图片列表（文件路径或base64字符串）
        
        Returns:
            types.Part 列表
        """
        parts = [types.Part(text=text)]
        
        if images:
            for img in images:
                if os.path.isfile(img):
                    # 本地文件
                    mime_type, base64_data = self._load_image_as_base64(img)
                else:
                    # 假设是 base64 字符串
                    mime_type = "image/jpeg"
                    base64_data = img
                
                parts.append(types.Part(
                    inline_data=types.Blob(
                        mime_type=mime_type,
                        data=base64_data
                    )
                ))
        
        return parts
    
    def chat(
        self,
        text: str,
        images: Optional[List[str]] = None,
        model: Optional[str] = None
    ) -> str:
        """
        文本对话模式（可带图片输入，返回文本）
        
        Args:
            text: 文本提示
            images: 图片列表（可选），支持文件路径或base64字符串
            model: 指定模型（可选，默认使用 text_model）
        
        Returns:
            AI 返回的文本内容
        
        Examples:
            >>> client.chat("你好")
            '你好！有什么可以帮助你的？'
            
            >>> client.chat("描述这张图片", images=["photo.jpg"])
            '这是一张...'
        """
        model = model or self.text_model
        parts = self._build_parts(text, images)
        
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=[types.Content(parts=parts)],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level)
                )
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"[GeminiClient] chat 调用失败: {e}")
            raise
    
    def generate_image(
        self,
        text: str,
        images: Optional[List[str]] = None,
        model: Optional[str] = None
    ) -> Optional[Image.Image]:
        """
        图片生成模式（传入文本和可选图片，返回生成的图片）
        
        Args:
            text: 文本提示（描述要生成或编辑的图片）
            images: 输入图片列表（可选），用于图片编辑场景
            model: 指定模型（可选，默认使用 image_model）
        
        Returns:
            PIL.Image.Image 对象，如果没有生成图片则返回 None
        
        Examples:
            >>> # 纯文本生成图片
            >>> image = client.generate_image("画一只可爱的柴犬")
            >>> image.save("dog.png")
            
            >>> # 图片编辑
            >>> image = client.generate_image("把水果换成香蕉", images=["fruit.jpg"])
            >>> image.save("edited.png")
        """
        model = model or self.image_model
        parts = self._build_parts(text, images)
        
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=[types.Content(parts=parts)],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=self.aspect_ratio,
                        image_size=self.image_size
                    )
                )
            )
            
            # 提取图片
            image_parts = [part for part in response.parts if part.inline_data]
            if image_parts:
                # 从 inline_data 创建 PIL Image
                inline_data = image_parts[0].inline_data
                # logger.debug(f"inline_data type: {type(inline_data)}")
                # logger.debug(f"inline_data.data type: {type(inline_data.data)}")
                # logger.debug(f"inline_data.data[:50]: {inline_data.data[:50] if inline_data.data else None}")
                # logger.debug(f"inline_data.mime_type: {inline_data.mime_type}")
                
                # data 可能是 bytes 或 base64 字符串
                data = inline_data.data
                if isinstance(data, bytes):
                    image_bytes = data
                elif isinstance(data, str):
                    image_bytes = base64.b64decode(data)
                else:
                    # 尝试直接转 bytes
                    image_bytes = bytes(data)
                return Image.open(BytesIO(image_bytes))
            
            # 没有图片，可能返回了文本
            if response.text:
                logger.warning(f"[GeminiClient] 未生成图片，返回文本: {response.text[:100]}")
            return None
            
        except Exception as e:
            logger.error(f"[GeminiClient] generate_image 调用失败: {e}")
            raise
    
    def generate_image_with_text(
        self,
        text: str,
        images: Optional[List[str]] = None,
        model: Optional[str] = None
    ) -> Tuple[Optional[Image.Image], str]:
        """
        图片生成模式，同时返回图片和可能的文本响应
        
        Args:
            text: 文本提示
            images: 输入图片列表（可选）
            model: 指定模型（可选）
        
        Returns:
            (image, text) 元组，image 可能为 None
        """
        model = model or self.image_model
        parts = self._build_parts(text, images)
        
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=[types.Content(parts=parts)],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=self.aspect_ratio,
                        image_size=self.image_size
                    )
                )
            )
            
            # 提取图片
            image_parts = [part for part in response.parts if part.inline_data]
            if image_parts:
                inline_data = image_parts[0].inline_data
                if isinstance(inline_data.data, bytes):
                    image_bytes = inline_data.data
                else:
                    image_bytes = base64.b64decode(inline_data.data)
                image = Image.open(BytesIO(image_bytes))
            else:
                image = None
            
            # 提取文本
            text_response = response.text or ""
            
            return image, text_response
            
        except Exception as e:
            logger.error(f"[GeminiClient] generate_image_with_text 调用失败: {e}")
            raise


