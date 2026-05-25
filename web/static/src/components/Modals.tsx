import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  X, FileText, Music, Video, Camera, Terminal, Waves,
  BrainCircuit, Activity, Upload, AlertTriangle, Play, HelpCircle
} from 'lucide-react';

interface ModalsProps {
  isOpen: boolean;
  onClose: () => void;
  defaultTab?: string;
  apiCall: (path: string, options?: RequestInit) => Promise<Response>;
  onAddMessage: (text: string, role: 'user' | 'agent' | 'system', showSpeak?: boolean) => void;
}

export default function Modals({
  isOpen,
  onClose,
  defaultTab = 'document',
  apiCall,
  onAddMessage
}: ModalsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // Camera states
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setActiveTab(defaultTab);
  }, [defaultTab, isOpen]);

  // Handle Drag & Drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  };

  // Upload file logic
  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadStatus('Please select a file first.');
      return;
    }

    setLoading(true);
    setUploadStatus('正在上传分析中，请稍后...');

    const formData = new FormData();
    formData.append('file', selectedFile);

    let endpoint = '/api/upload/document';
    if (activeTab === 'audio') endpoint = '/api/upload/audio';
    if (activeTab === 'video') endpoint = '/api/upload/video';

    try {
      const resp = await apiCall(endpoint, {
        method: 'POST',
        body: formData,
      });

      const data = await resp.json();
      if (resp.ok) {
        onAddMessage(`[系统] 成功成功载入: ${selectedFile.name} (${formatSize(selectedFile.size)})`, 'system');
        if (data.preview) {
          onAddMessage(`[文档预览] ${data.preview.substring(0, 1000)}`, 'agent', true);
        }

        // Implicit analysis step
        if (activeTab === 'document' && data.preview) {
          onAddMessage(`[系统] 正在帮您分析并提炼文档核心实体和建议...`, 'system');
          const chatResp = await apiCall('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: `请帮我分析这份文档的核心内容，提炼关键观点和行动建议。`,
              context_type: 'document',
              context_summary: `文档: ${data.filename}`
            })
          });
          const chatData = await chatResp.json();
          onAddMessage(chatData.analysis || '文档已经挂载到您的认知库中。', 'agent', true);
        }

        setSelectedFile(null);
        setUploadStatus('');
        onClose();
      } else {
        setUploadStatus(data.error || '上传失败，请重新检查格式。');
      }
    } catch (e) {
      setUploadStatus('网络通道错误，无法挂载文件。');
    } finally {
      setLoading(false);
    }
  };

  // Camera handling
  const toggleCamera = async () => {
    if (cameraActive) {
      stopCamera();
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        setCameraStream(stream);
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setCameraActive(true);
      } catch (e) {
        onAddMessage('[摄像头] 获取音视轨道失败，请确认权限和连接', 'system');
      }
    }
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(t => t.stop());
      setCameraStream(null);
    }
    setCameraActive(false);
  };

  const handleCaptureSnapshot = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    canvasRef.current.width = videoRef.current.videoWidth;
    canvasRef.current.height = videoRef.current.videoHeight;
    ctx.drawImage(videoRef.current, 0, 0);

    const snapshot = canvasRef.current.toDataURL('image/png');
    setLoading(true);

    try {
      const resp = await apiCall('/api/upload/camera', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: snapshot }),
      });
      const data = await resp.json();
      if (resp.ok) {
        onAddMessage(`[网络摄像] 已获取帧并在神经网络库中进行了场景描述。`, 'system');
        onClose();
      }
    } catch (e) {
      onAddMessage('[摄像头] 上传识别画面错误', 'system');
    } finally {
      setLoading(false);
      stopCamera();
    }
  };

  useEffect(() => {
    return () => {
      // clean tracks when modal unmount
      if (cameraStream) {
        cameraStream.getTracks().forEach(t => t.stop());
      }
    };
  }, [cameraStream]);

  if (!isOpen) return null;

  const tabsConfig = [
    { key: 'document', label: '文档', icon: FileText },
    { key: 'audio', label: '音频', icon: Music },
    { key: 'video', label: '视频', icon: Video },
    { key: 'camera', label: '摄像头', icon: Camera },
    { key: 'stream', label: '网络拉流', icon: Waves, isSub: true },
    { key: 'bci', label: '脑机 EEG', icon: BrainCircuit, isSub: true },
    { key: 'sensor', label: '体感雷达', icon: Activity, isSub: true },
  ];

  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center bg-black/60 backdrop-blur-md p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.98 }}
        className="w-full max-w-2xl bg-[#0a0a14]/90 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-3xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header bar */}
        <div className="p-4.5 bg-white/5 border-b border-white/10 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white font-sans tracking-wide">多模态认知输入载体</h3>
          <button
            onClick={() => {
              stopCamera();
              onClose();
            }}
            className="p-1 rounded text-white/40 hover:text-white hover:bg-white/10 active:scale-90 transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab selection matrix */}
        <div className="px-5 py-3 bg-white/5 border-b border-white/10 flex flex-wrap items-center gap-1.5 overflow-x-auto select-none">
          {tabsConfig.map((tab) => {
            const IconComponent = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => {
                  stopCamera();
                  setActiveTab(tab.key);
                  setSelectedFile(null);
                  setUploadStatus('');
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer tracking-wide transition-all ${
                  isActive
                    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-md shadow-blue-950/20'
                    : tab.isSub
                    ? 'text-white/30 border border-transparent font-medium hover:text-white/60'
                    : 'text-white/60 border border-transparent hover:text-white hover:bg-white/5'
                }`}
              >
                <IconComponent className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content body based on active tabs */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <AnimatePresence mode="wait">
            {/* Tabs: Documents / Audios / Videos */}
            {(activeTab === 'document' || activeTab === 'audio' || activeTab === 'video') && (
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-4"
              >
                {/* Drag and drop panel area */}
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center gap-3 transition-all cursor-pointer ${
                    dragOver
                      ? 'border-purple-500 bg-purple-500/5 text-purple-400'
                      : 'border-white/10 hover:border-purple-500/30 hover:bg-slate-950/20 text-slate-400'
                  }`}
                >
                  <div className="w-12 h-12 rounded-xl bg-slate-950/80 border border-white/5 flex items-center justify-center text-slate-400 group-hover:text-purple-400 transition-colors">
                    <Upload className="w-6 h-6" />
                  </div>
                  <div className="text-center">
                    <p className="text-xs font-semibold text-slate-200">
                      拖拽或点击本区域检索文件并挂载
                    </p>
                    <p className="text-3xs text-slate-500 mt-1 uppercase tracking-widest font-mono">
                      {activeTab === 'document'
                        ? '支持 .txt, .md, .py, .json, .csv, .pdf 和 .docx'
                        : activeTab === 'audio'
                        ? '支持 .mp3, .wav, .m4a 和 .ogg 离线音频转写'
                        : '支持 .mp4, .mov, .avi 序列关键帧视觉分析'}
                    </p>
                  </div>
                </div>

                {/* File selectors */}
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileChange}
                  accept={
                    activeTab === 'document'
                      ? '.txt,.md,.py,.json,.csv,.pdf,.docx'
                      : activeTab === 'audio'
                      ? '.mp3,.wav,.m4a,.ogg,.webm'
                      : '.mp4,.mov,.avi,.webm'
                  }
                  className="hidden"
                />

                {/* Attachment report card */}
                {selectedFile && (
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-sky-500/10 flex items-center justify-between">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 rounded bg-sky-500/10 flex items-center justify-center text-sky-400 flex-shrink-0">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-300 truncate">{selectedFile.name}</p>
                        <p className="text-[10px] font-mono text-slate-500">{formatSize(selectedFile.size)}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedFile(null)}
                      className="p-1 text-slate-500 hover:text-white transition-colors cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}

                {/* Upload Status message warnings */}
                {uploadStatus && (
                  <div className="p-3 bg-purple-500/5 text-purple-400 rounded-xl border border-purple-500/10 text-xs">
                    {uploadStatus}
                  </div>
                )}

                {/* Active placeholders for non-primary features and controls */}
                {activeTab !== 'document' && (
                  <div className="flex items-start gap-2 p-3 bg-amber-500/5 text-amber-500/80 rounded-xl border border-amber-500/10 text-xs leading-relaxed">
                    <AlertTriangle className="w-4.5 h-4.5 text-amber-500 mt-0.5 flex-shrink-0" />
                    <span>
                      系统后置规划：上传此类富媒体文件后，后台将调用语音 Whisper 兼容引擎或视觉分析模块将数据转化为特征矢量提取，目前支持基本的上传链路。
                    </span>
                  </div>
                )}

                <div className="flex gap-2.5 justify-end">
                  <button
                    onClick={() => {
                      setSelectedFile(null);
                      setUploadStatus('');
                      onClose();
                    }}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 rounded-lg cursor-pointer"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleUpload}
                    disabled={!selectedFile || loading}
                    className="px-5 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-xs font-semibold text-white rounded-lg transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    {loading ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <>
                        <Upload className="w-3.5 h-3.5" />
                        <span>确认上传并提炼</span>
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            )}

            {/* Tab: Real Camera devices snapshotting */}
            {activeTab === 'camera' && (
              <motion.div
                key="camera"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4 flex flex-col items-center"
              >
                <div className="relative w-full max-w-md h-[280px] bg-slate-950 rounded-2xl border border-white/5 overflow-hidden flex items-center justify-center">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    className="w-full h-full object-cover"
                    style={{ display: cameraActive ? 'block' : 'none' }}
                  />
                  <canvas ref={canvasRef} className="hidden" />

                  {!cameraActive && (
                    <div className="text-center p-6 text-slate-500 flex flex-col items-center gap-2">
                      <Camera className="w-12 h-12 text-slate-700 animate-pulse" />
                      <p className="text-xs font-semibold text-slate-400">摄像头未启动</p>
                      <p className="text-3xs text-slate-600 font-mono tracking-wide uppercase">CAMERA HARDWARE STREAMING PORT</p>
                    </div>
                  )}
                </div>

                <div className="p-3 bg-sky-500/5 text-sky-400 rounded-xl border border-sky-500/10 text-xs max-w-md w-full leading-relaxed">
                  系统后置规划：支持摄入关键画面，后台调用 Gemini 多模态模型结合个人画像完成全域情境分析及注意力捕获。
                </div>

                <div className="flex gap-2.5">
                  <button
                    onClick={toggleCamera}
                    className="px-4.5 py-2.5 bg-slate-800 border border-white/5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white transition-all cursor-pointer"
                  >
                    {cameraActive ? '停止摄像头' : '启动摄像头'}
                  </button>
                  <button
                    onClick={handleCaptureSnapshot}
                    disabled={!cameraActive || loading}
                    className="px-4.5 py-2.5 bg-sky-600 disabled:opacity-40 border border-sky-500/20 rounded-lg text-xs font-bold text-white shadow-lg transition-all flex items-center gap-1.5 cursor-pointer"
                  >
                    {loading ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <>
                        <Camera className="w-3.5 h-3.5 animate-pulse" />
                        <span>拍照并上传分析</span>
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            )}

            {/* Tabs: Placeholder Advanced Streams */}
            {(activeTab === 'stream' || activeTab === 'bci' || activeTab === 'sensor') && (
              <motion.div
                key={activeTab}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="py-12 flex flex-col items-center text-center max-w-md mx-auto space-y-4"
              >
                {activeTab === 'stream' ? (
                  <Waves className="w-14 h-14 text-purple-400 animate-pulse" />
                ) : activeTab === 'bci' ? (
                  <BrainCircuit className="w-14 h-14 text-cyan-400 animate-pulse" />
                ) : (
                  <Activity className="w-14 h-14 text-purple-400 animate-bounce" />
                )}

                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono">
                    {activeTab === 'stream' ? 'RTSP/RTMP 外部视频拉流接入' : activeTab === 'bci' ? '脑机接口（BCI EEG）遥测通道' : '触觉体感/力反馈传感器接口'}
                  </h4>
                  <p className="text-xs text-slate-500 leading-relaxed font-sans">
                    这是系统极高规格的预留认知通道。当您佩戴外置认知捕捉芯片、便携脑电图追踪设备或挂载远程姿态反馈摄像头时，在此处载入以启动协同生命周期分析。
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-dashed border-white/10 w-full text-left space-y-2">
                  <span className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">仿真硬件流虚拟定义：</span>
                  <input
                    type="text"
                    placeholder={activeTab === 'stream' ? "rtsp://192.168.1.102:554/growth_stream" : activeTab === 'bci' ? "eeg_telemetry://bci_module_channel_7" : "sensor_feedback://axis_gyroscope_data"}
                    className="w-full px-2.5 py-1.5 rounded-lg text-xs font-mono select-all text-slate-400 glass-input bg-slate-900 border-white/5"
                    disabled
                  />
                </div>

                <button
                  disabled
                  className="px-5 py-2.5 bg-slate-800 border border-slate-700/60 text-slate-500 font-bold rounded-lg text-xs tracking-wider uppercase disabled:cursor-not-allowed"
                >
                  挂载底层传感器 (开发中)
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
