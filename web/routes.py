"""
Web API 路由 — 所有 REST 接口 (多用户支持)
扩展支持: 语音输入、文档/音频/视频上传预留入口、SSE 流式对话
"""

import json
import os
import base64
import asyncio
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user, create_user, verify_user, create_access_token

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
    return JSONResponse(request.app.state.get_agent(user_id).memory.get_profile())


# ========== Goals ==========
@router.post("/api/goals")
async def add_goal(req: GoalRequest, request: Request, user_id: str = Depends(get_current_user)):
    request.app.state.get_agent(user_id).add_goal(req.goal, req.priority)
    return JSONResponse({"status": "ok"})


@router.get("/api/goals")
async def list_goals(request: Request, user_id: str = Depends(get_current_user)):
    return JSONResponse(request.app.state.get_agent(user_id).memory.list_goals("active"))


# ========== Abilities ==========
@router.post("/api/abilities")
async def add_ability(req: AbilityRequest, request: Request, user_id: str = Depends(get_current_user)):
    request.app.state.get_agent(user_id).add_ability(req.name, req.level)
    return JSONResponse({"status": "ok"})


@router.get("/api/abilities")
async def list_abilities(request: Request, user_id: str = Depends(get_current_user)):
    return JSONResponse(request.app.state.get_agent(user_id).memory.list_abilities())


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
    try:
        text = content.decode("utf-8")[:10000]
    except UnicodeDecodeError:
        text = f"[二进制文件] {filename} ({len(content)} bytes) - 全文解析功能即将上线"

    if request:
        agent = request.app.state.get_agent(user_id)
        agent.memory.add_history(
            entry_type="document", content=f"上传文档: {filename}",
            metadata={"filename": filename, "size": len(content)}
        )
        agent.vector.add(
            content=f"文档 {filename}: {text[:1000]}",
            category="document",
            metadata={"filename": filename, "size": len(content)}
        )

    return JSONResponse({
        "status": "ok", "filename": filename, "size": len(content),
        "preview": text[:2000],
        "message": f"文档 '{filename}' 已接收，内容已存入记忆库。"
    })


@router.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...), request: Request = None,
                       user_id: str = Depends(get_current_user)):
    content = await file.read()
    filename = file.filename or "unknown"
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    save_path = os.path.join(uploads_dir, filename)
    with open(save_path, "wb") as f:
        f.write(content)

    if request:
        agent = request.app.state.get_agent(user_id)
        agent.memory.add_history(
            entry_type="audio_upload", content=f"上传音频: {filename}",
            metadata={"filename": filename, "size": len(content), "path": save_path}
        )

    return JSONResponse({
        "status": "ok", "filename": filename, "size": len(content),
        "message": f"音频 '{filename}' 已保存。语音转文字功能即将上线。",
        "future_feature": "speech-to-text"
    })


@router.post("/api/upload/video")
async def upload_video(file: UploadFile = File(...), request: Request = None,
                       user_id: str = Depends(get_current_user)):
    content = await file.read()
    filename = file.filename or "unknown"
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    save_path = os.path.join(uploads_dir, filename)
    with open(save_path, "wb") as f:
        f.write(content)

    if request:
        agent = request.app.state.get_agent(user_id)
        agent.memory.add_history(
            entry_type="video_upload", content=f"上传视频: {filename}",
            metadata={"filename": filename, "size": len(content), "path": save_path}
        )

    return JSONResponse({
        "status": "ok", "filename": filename, "size": len(content),
        "message": f"视频 '{filename}' 已保存。视频分析功能即将上线。",
        "future_feature": "video-analysis"
    })


@router.post("/api/upload/camera")
async def upload_camera(request: Request, user_id: str = Depends(get_current_user)):
    body = await request.body()
    data = json.loads(body)
    image_b64 = data.get("image", "")

    if image_b64:
        uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        import time
        filename = f"camera_{int(time.time())}.png"
        save_path = os.path.join(uploads_dir, filename)
        with open(save_path, "wb") as f:
            f.write(base64.b64decode(image_b64.split(",")[-1]))

        agent = request.app.state.get_agent(user_id)
        agent.memory.add_history(
            entry_type="camera", content="摄像头截图",
            metadata={"filename": filename, "path": save_path}
        )

        return JSONResponse({
            "status": "ok", "filename": filename,
            "message": "截图已保存。图像分析功能即将上线。",
            "future_feature": "image-vision-analysis"
        })

    return JSONResponse({"status": "error", "message": "未收到图像数据"}, status_code=400)


@router.get("/api/uploads/history")
async def get_upload_history(request: Request, user_id: str = Depends(get_current_user),
                             category: str = None):
    agent = request.app.state.get_agent(user_id)
    if category:
        entries = agent.vector.search_by_category(category, top_k=20)
    else:
        entries = agent.vector.search_by_category("document", top_k=10)
        entries += agent.vector.search_by_category("audio_upload", top_k=5)
        entries += agent.vector.search_by_category("video_upload", top_k=5)
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
