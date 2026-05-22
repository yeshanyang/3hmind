"""
Web API 路由 — 所有 REST 接口 (多用户支持)
统一智能体: 语音输入、文档/音频/视频上传、SSE 流式对话
"""

import json
import os
import io
import base64
import asyncio
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI

from config import settings
from auth import get_current_user, create_user, verify_user, create_access_token
from input_layer.document_processor import DocumentProcessor

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context_type: str = "text"  # text | voice | document | video
    context_summary: str = ""   # 附加上下文描述


class ProfileRequest(BaseModel):
    role: str = ""
    current_situation: str = ""
    emotional_state: str = ""


class GoalRequest(BaseModel):
    goal: str
    priority: int = 1


class AbilityRequest(BaseModel):
    name: str
    level: str = "beginner"


class LoginRequest(BaseModel):
    username: str
    password: str


# ========== 页面 (无需登录) ==========
@router.get("/", response_class=HTMLResponse)
async def index():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()


# ========== 认证 ==========
@router.post("/api/auth/register")
async def register(req: LoginRequest):
    success, msg = create_user(req.username, req.password)
    if not success:
        return JSONResponse({"error": msg}, status_code=400)
    token = verify_user(req.username, req.password)
    return JSONResponse({"token": token, "username": req.username.strip().lower(), "message": msg})


@router.post("/api/auth/login")
async def login(req: LoginRequest):
    token = verify_user(req.username, req.password)
    if token is None:
        return JSONResponse({"error": "用户名或密码错误"}, status_code=401)
    return JSONResponse({"token": token, "username": req.username.strip().lower()})


@router.get("/api/auth/me")
async def me(user_id: str = Depends(get_current_user)):
    return JSONResponse({"username": user_id})


# ========== 对话 (扩展: 支持多模态上下文) ==========
@router.post("/api/chat")
async def chat(req: ChatRequest, request: Request, user_id: str = Depends(get_current_user)):
    agent = request.app.state.get_agent(user_id)

    prefix = ""
    if req.context_type == "voice":
        prefix = "[语音输入] "
    elif req.context_type == "document":
        prefix = f"[文档内容] {req.context_summary}\n"
    elif req.context_type == "video":
        prefix = f"[视频描述] {req.context_summary}\n"

    full_message = prefix + req.message
    result = await asyncio.to_thread(agent.chat, full_message)
    return JSONResponse(result)


# ========== 流式对话 (SSE) — 在线语音对话模式 ==========
@router.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request, user_id: str = Depends(get_current_user)):
    """SSE 流式聊天，用于在线语音对话模式，逐 token 推送"""
    agent = request.app.state.get_agent(user_id)
    prefix = ""
    if req.context_type == "voice":
        prefix = "[语音输入] "
    full_message = prefix + req.message

    async def event_generator():
        try:
            loop = asyncio.get_event_loop()
            gen = agent.chat_stream(full_message)
            for token in gen:
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ========== 复盘 ==========
@router.post("/api/review")
async def review(request: Request, user_id: str = Depends(get_current_user)):
    result = await asyncio.to_thread(request.app.state.get_agent(user_id).review)
    return JSONResponse({"result": result})


# ========== 成长方案 ==========
@router.post("/api/plan")
async def plan(request: Request, user_id: str = Depends(get_current_user),
               gap_area: str = None):
    result = await asyncio.to_thread(request.app.state.get_agent(user_id).plan, gap_area)
    return JSONResponse({"result": result})


# ========== 督促 ==========
@router.post("/api/nudge")
async def nudge(request: Request, user_id: str = Depends(get_current_user)):
    result = await asyncio.to_thread(request.app.state.get_agent(user_id).nudge)
    return JSONResponse({"result": result})


# ========== 仪表盘 ==========
@router.get("/api/dashboard")
async def dashboard(request: Request, user_id: str = Depends(get_current_user)):
    result = await asyncio.to_thread(request.app.state.get_agent(user_id).show_dashboard)
    return JSONResponse({"result": result})


# ========== Profile ==========
@router.post("/api/profile")
async def update_profile(req: ProfileRequest, request: Request, user_id: str = Depends(get_current_user)):
    agent = request.app.state.get_agent(user_id)
    agent.update_profile(
        role=req.role,
        current_situation=req.current_situation,
        emotional_state=req.emotional_state
    )
    return JSONResponse({"status": "ok"})


@router.get("/api/profile")
async def get_profile(request: Request, user_id: str = Depends(get_current_user)):
    return JSONResponse(request.app.state.get_agent(user_id).mind.get_profile())


# ========== Goals ==========
@router.post("/api/goals")
async def add_goal(req: GoalRequest, request: Request, user_id: str = Depends(get_current_user)):
    request.app.state.get_agent(user_id).add_goal(req.goal, req.priority)
    return JSONResponse({"status": "ok"})


@router.get("/api/goals")
async def list_goals(request: Request, user_id: str = Depends(get_current_user)):
    return JSONResponse(request.app.state.get_agent(user_id).mind.list_goals("active"))


@router.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: int, request: Request, user_id: str = Depends(get_current_user)):
    request.app.state.get_agent(user_id).delete_goal(goal_id)
    return JSONResponse({"status": "ok"})


class ProgressRequest(BaseModel):
    progress: int

@router.patch("/api/goals/{goal_id}/progress")
async def update_goal_progress(goal_id: int, req: ProgressRequest, request: Request, user_id: str = Depends(get_current_user)):
    request.app.state.get_agent(user_id).update_goal_progress(goal_id, req.progress)
    return JSONResponse({"status": "ok"})


# ========== Abilities ==========
@router.post("/api/abilities")
async def add_ability(req: AbilityRequest, request: Request, user_id: str = Depends(get_current_user)):
    request.app.state.get_agent(user_id).add_ability(req.name, req.level)
    return JSONResponse({"status": "ok"})


@router.get("/api/abilities")
async def list_abilities(request: Request, user_id: str = Depends(get_current_user)):
    return JSONResponse(request.app.state.get_agent(user_id).mind.list_abilities())


# ========== 自主消息轮询 ==========
@router.get("/api/poll")
async def poll_autonomous(request: Request, user_id: str = Depends(get_current_user)):
    pending = request.app.state.scheduler.get_pending(user_id)
    return JSONResponse(pending if pending else {})


# ========== 画像探索 (交互式获取) ==========
@router.get("/api/profile/status")
async def profile_status(request: Request, user_id: str = Depends(get_current_user)):
    return JSONResponse(request.app.state.get_agent(user_id).interaction.profile_status())


@router.get("/api/profile/discover")
async def profile_discover(request: Request, user_id: str = Depends(get_current_user)):
    agent = request.app.state.get_agent(user_id)
    question = agent.reasoning.generate_discovery_question()
    status = agent.interaction.profile_status()
    return JSONResponse({"question": question, "status": status})


# ========== 状态概览 ==========
@router.get("/api/status")
async def status(request: Request, user_id: str = Depends(get_current_user)):
    agent = request.app.state.get_agent(user_id)
    situation = agent.perception.assess_situation()
    intervene, reason = agent.perception.should_intervene()
    return JSONResponse({
        "situation": situation,
        "should_intervene": intervene,
        "intervene_reason": reason
    })


# ========== AI 主动追问 (在线语音对话模式) ==========
class FollowUpRequest(BaseModel):
    last_user_msg: str = ""
    last_ai_response: str = ""


@router.post("/api/proactive/question")
async def proactive_question(req: FollowUpRequest, request: Request, user_id: str = Depends(get_current_user)):
    agent = request.app.state.get_agent(user_id)
    question = await asyncio.to_thread(agent.generate_follow_up_question, req.last_user_msg, req.last_ai_response)
    return JSONResponse({"question": question})


# ========== 追问会话 (Inquiry Session) — 深度对话模式 ==========
class InquiryStartRequest(BaseModel):
    topic: str = ""


class InquiryNextRequest(BaseModel):
    answer: str = ""


@router.post("/api/inquiry/start")
async def inquiry_start(req: InquiryStartRequest, request: Request, user_id: str = Depends(get_current_user)):
    result = await asyncio.to_thread(request.app.state.get_agent(user_id).inquiry_start, req.topic)
    return JSONResponse(result)


@router.post("/api/inquiry/next")
async def inquiry_next(req: InquiryNextRequest, request: Request, user_id: str = Depends(get_current_user)):
    result = await asyncio.to_thread(request.app.state.get_agent(user_id).inquiry_next, req.answer)
    return JSONResponse(result)


@router.get("/api/inquiry/status")
async def inquiry_status(request: Request, user_id: str = Depends(get_current_user)):
    return JSONResponse(request.app.state.get_agent(user_id).inquiry_status())


@router.post("/api/inquiry/stop")
async def inquiry_stop(request: Request, user_id: str = Depends(get_current_user)):
    result = await asyncio.to_thread(request.app.state.get_agent(user_id).inquiry_stop)
    return JSONResponse(result)


# ============================================================
# 多模态输入预留接口
# ============================================================

@router.post("/api/upload/document")
async def upload_document(file: UploadFile = File(...), request: Request = None,
                          user_id: str = Depends(get_current_user)):
    content = await file.read()
    filename = file.filename or "unknown"
    agent = request.app.state.get_agent(user_id) if request else None
    processor = DocumentProcessor(agent.mind if agent else None)
    return JSONResponse(processor.process_document(content, filename))


@router.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...), request: Request = None,
                       user_id: str = Depends(get_current_user)):
    content = await file.read()
    filename = file.filename or "unknown"
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    agent = request.app.state.get_agent(user_id) if request else None
    processor = DocumentProcessor(agent.mind if agent else None)
    return JSONResponse(processor.process_audio(content, filename, uploads_dir))


# ========== 语音转文字 (STT) ==========

def _get_stt_client():
    """创建 STT 客户端，优先使用独立配置，否则复用 LLM API"""
    key = settings.stt_api_key or settings.llm_api_key
    url = settings.stt_base_url or settings.llm_base_url
    if not key:
        return None
    return OpenAI(api_key=key, base_url=url)


@router.post("/api/stt")
async def speech_to_text(file: UploadFile = File(...),
                         user_id: str = Depends(get_current_user)):
    """浏览器录音上传 → Whisper API 转写 → 返回文本"""
    client = _get_stt_client()
    if not client:
        return JSONResponse({"error": "STT 服务未配置，请设置 STT_API_KEY"}, status_code=503)

    audio_bytes = await file.read()
    filename = (file.filename or "recording.webm").lower()

    # 推断 MIME 类型
    ext_to_mime = {
        ".webm": "audio/webm", ".mp3": "audio/mpeg", ".wav": "audio/wav",
        ".m4a": "audio/mp4", ".ogg": "audio/ogg", ".flac": "audio/flac",
        ".mp4": "audio/mp4", ".opus": "audio/ogg",
    }
    ext = os.path.splitext(filename)[1]
    content_type = ext_to_mime.get(ext, "audio/webm")

    # 如果文件没有扩展名，尝试从内容推断
    if not ext:
        content_type = "audio/webm"  # 默认 MediaRecorder 格式

    try:
        result = client.audio.transcriptions.create(
            model=settings.stt_model,
            file=(filename, audio_bytes, content_type),
            language="zh",
            response_format="text",
        )
        text = result.strip() if isinstance(result, str) else str(result)
        return JSONResponse({"text": text, "filename": filename})
    except Exception as e:
        err_msg = str(e)
        # 常见错误友好提示
        if "404" in err_msg or "not found" in err_msg.lower():
            return JSONResponse(
                {"error": f"当前 API 不支持语音转文字 ({settings.stt_base_url or settings.llm_base_url})。"
                           "请配置 STT_BASE_URL 指向支持 Whisper 的 API。"},
                status_code=503)
        return JSONResponse({"error": f"语音识别失败: {err_msg}"}, status_code=500)


@router.post("/api/upload/video")
async def upload_video(file: UploadFile = File(...), request: Request = None,
                       user_id: str = Depends(get_current_user)):
    content = await file.read()
    filename = file.filename or "unknown"
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    agent = request.app.state.get_agent(user_id) if request else None
    processor = DocumentProcessor(agent.mind if agent else None)
    return JSONResponse(processor.process_video(content, filename, uploads_dir))


@router.post("/api/upload/camera")
async def upload_camera(request: Request, user_id: str = Depends(get_current_user)):
    body = await request.body()
    data = json.loads(body)
    image_b64 = data.get("image", "")
    if not image_b64:
        return JSONResponse({"status": "error", "message": "未收到图像数据"}, status_code=400)
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    agent = request.app.state.get_agent(user_id)
    processor = DocumentProcessor(agent.mind if agent else None)
    return JSONResponse(processor.process_camera(image_b64, uploads_dir))


@router.get("/api/uploads/history")
async def get_upload_history(request: Request, user_id: str = Depends(get_current_user),
                             category: str = None):
    agent = request.app.state.get_agent(user_id)
    if category:
        entries = agent.mind.vector.search_by_category(category, top_k=20)
    else:
        entries = agent.mind.vector.search_by_category("document", top_k=10)
        entries += agent.mind.vector.search_by_category("audio_upload", top_k=5)
        entries += agent.mind.vector.search_by_category("video_upload", top_k=5)
    return JSONResponse(entries)


# ============================================================
# 话题记忆 (Topic Memory) API
# ============================================================

@router.get("/api/topics")
async def list_topics(request: Request, user_id: str = Depends(get_current_user)):
    return JSONResponse(request.app.state.get_agent(user_id).list_topics())


@router.get("/api/topics/search")
async def search_topics(q: str = "", request: Request = None,
                        user_id: str = Depends(get_current_user)):
    if not q:
        return JSONResponse([])
    return JSONResponse(request.app.state.get_agent(user_id).search_topics(q))


@router.get("/api/topics/{topic_slug}")
async def get_topic(topic_slug: str, request: Request = None,
                    user_id: str = Depends(get_current_user)):
    detail = request.app.state.get_agent(user_id).get_topic(topic_slug)
    if not detail:
        return JSONResponse({"error": "话题不存在"}, status_code=404)
    return JSONResponse(detail)


@router.post("/api/topics/optimize")
async def optimize_topics(request: Request = None, user_id: str = Depends(get_current_user),
                          topic_slug: str = None):
    result = await asyncio.to_thread(request.app.state.get_agent(user_id).optimize_topic, topic_slug)
    return JSONResponse(result)


class TopicPriorityRequest(BaseModel):
    topic_slug: str
    priority: int


@router.post("/api/topics/priority")
async def set_topic_priority(req: TopicPriorityRequest, request: Request = None,
                             user_id: str = Depends(get_current_user)):
    result = request.app.state.get_agent(user_id).set_topic_priority(req.topic_slug, req.priority)
    return JSONResponse(result)
