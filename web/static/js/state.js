// ==================== 全局状态 ====================
let authToken = localStorage.getItem('3hmind_token') || '';
let currentUser = '';

let polling = null;
let recognition = null;
let synth = window.speechSynthesis;
let synthReady = false;
let synthVoice = null;

// 语音在线模式
let convMode = false;
let convState = 'idle';       // idle | listening | processing | speaking
let _exitingVoiceMode = false;
let autoSpeakEnabled = true;
let micGated = false;

// AI 主动追问
let autoAskEnabled = true;
let lastUserMsg = '';
let lastAiResponse = '';

let sendLocked = false;

// 深度对话
let inquiryActive = false;
let inquiryQuestions = [];
let inquiryIndex = 0;
let inquiryTopic = '';
let waitingForInquiryAnswer = false;

// 语音输入
let voiceTranscript = '';
let voiceInputActive = false;    // 语音输入框是否处于活跃输入状态
let voiceFinalText = '';         // 语音识别最终文本
let silenceTimer = null;
let silenceCountdown = 0;
let countdownInterval = null;
let silenceHandled = false;
let _networkErrCount = 0;
let _useMediaRecorder = false;
let mediaRecorder = null;
let mediaChunks = [];
let _lastInputWasVoice = false;
let _savedTypedText = '';        // 保存用户在语音启动前手动输入的文本
let _voicePaused = false;        // 语音对话模式中临时暂停（手动打断去打字）
let _typingWatchTimer = null;    // 打字结束后自动恢复语音的计时器

// 语音输入结束词 — 检测到后结束当次语音输入（区别于 STOP_PHRASES 的停止对话）
const VOICE_INPUT_END_PHRASES = [
  '说完了', '就这样', '完毕', '好了', '可以了',
  '就这些', '先这样', '讲完了', '就到这里',
  '以上', '发送', '确认发送',
];

// 文件上传
let selectedFile = null;
let selectedFileType = null;
let cameraStream = null;

// 追问链
let followUpTimer = null;
let _followUpCount = 0;
const MAX_FOLLOW_UPS = 3;
const FOLLOW_UP_DELAYS = [10, 20, 30];

let ttsInterrupted = false;

// 流式 TTS
let _ttsQueue = [];
let _ttsBusy = false;
let _ttsSpokenLen = 0;
let _ttsActive = false;

// 静音检测常量
const SILENCE_LONG = 3;
const SILENCE_SHORT = 3;

// 句尾检测模式
const SENTENCE_END_PATTERNS = [
  /[吗呢吧啊呀哦嘛咯]$/,
  /[？?！!。，,～~]$/,
  /什么$/, /怎么$/, /为什么$/,
  /多少$/, /哪[个些种边]$/, /谁$/,
  /[了的]$/,
  /[好行对可]$/,
  /是不是$/, /能不能$/, /会不会$/, /可不可以$/,
  /[过完到]$/,
  /就这样$/, /这样做$/, /没问题$/,
  /[吧嘛][。！？]?$/,
  /.{0,2}[。！？]$/
];

// 停止对话关键词
const STOP_PHRASES = [
  '不要说了', '别说了', '停止', '闭嘴', '别问了', '不要问了',
  '关闭对话', '关闭语音', '结束对话', '再见', '拜拜', '休息吧',
  '不要沟通了', '不聊了', '别沟通了', '停止沟通',
];

// 渐进重启延迟
let _restartingListening = false;
let _restartCount = 0;
let _hasSpoken = false;
let _silentCycles = 0;           // 连续静音周期计数，用于触发追问
const RESTART_DELAYS = [2, 5, 10, 20, 30, 60];

const _SENTENCE_RE = /[。！？.!?\n]/;
