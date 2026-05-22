"""
文档处理器 — 从 web/routes.py 提取上传处理逻辑
支持 document / audio / video / camera 四种上传类型
"""

import os
import json
import base64


class DocumentProcessor:
    """处理多模态上传文件"""

    def __init__(self, mind=None):
        self.mind = mind

    def process_document(self, content: bytes, filename: str) -> dict:
        try:
            text = content.decode("utf-8")[:10000]
        except UnicodeDecodeError:
            text = f"[二进制文件] {filename} ({len(content)} bytes) - 全文解析功能即将上线"

        if self.mind:
            self.mind.add_history(
                entry_type="document", content=f"上传文档: {filename}",
                metadata={"filename": filename, "size": len(content)})
            self.mind.vector.add(
                content=f"文档 {filename}: {text[:1000]}",
                category="document",
                metadata={"filename": filename, "size": len(content)})

        return {
            "status": "ok", "filename": filename, "size": len(content),
            "preview": text[:2000],
            "message": f"文档 '{filename}' 已接收，内容已存入记忆库。"}

    def process_audio(self, content: bytes, filename: str, uploads_dir: str) -> dict:
        os.makedirs(uploads_dir, exist_ok=True)
        save_path = os.path.join(uploads_dir, filename)
        with open(save_path, "wb") as f:
            f.write(content)

        if self.mind:
            self.mind.add_history(
                entry_type="audio_upload", content=f"上传音频: {filename}",
                metadata={"filename": filename, "size": len(content), "path": save_path})

        return {
            "status": "ok", "filename": filename, "size": len(content),
            "message": f"音频 '{filename}' 已保存。语音转文字功能即将上线。"}

    def process_video(self, content: bytes, filename: str, uploads_dir: str) -> dict:
        os.makedirs(uploads_dir, exist_ok=True)
        save_path = os.path.join(uploads_dir, filename)
        with open(save_path, "wb") as f:
            f.write(content)

        if self.mind:
            self.mind.add_history(
                entry_type="video_upload", content=f"上传视频: {filename}",
                metadata={"filename": filename, "size": len(content), "path": save_path})

        return {
            "status": "ok", "filename": filename, "size": len(content),
            "message": f"视频 '{filename}' 已保存。视频分析功能即将上线。"}

    def process_camera(self, image_b64: str, uploads_dir: str) -> dict:
        if not image_b64:
            return {"status": "error", "message": "未收到图像数据"}

        os.makedirs(uploads_dir, exist_ok=True)
        import time
        filename = f"camera_{int(time.time())}.png"
        save_path = os.path.join(uploads_dir, filename)
        with open(save_path, "wb") as f:
            f.write(base64.b64decode(image_b64.split(",")[-1]))

        if self.mind:
            self.mind.add_history(
                entry_type="camera", content="摄像头截图",
                metadata={"filename": filename, "path": save_path})

        return {
            "status": "ok", "filename": filename,
            "message": "截图已保存。图像分析功能即将上线。"}
