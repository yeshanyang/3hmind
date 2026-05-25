import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ShieldCheck, User, Lock, ArrowRight, UserPlus, LogIn, AlertCircle } from 'lucide-react';

interface LoginOverlayProps {
  onLoginSuccess: (token: string, username: string) => void;
  apiCall: (path: string, options?: RequestInit) => Promise<Response>;
}

export default function LoginOverlay({ onLoginSuccess, apiCall }: LoginOverlayProps) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('请输入用户名和密码');
      return;
    }

    if (isRegister) {
      if (username.trim().length < 2) {
        setError('用户名至少需要2个字符');
        return;
      }
      if (password.length < 4) {
        setError('密码至少需要4个字符');
        return;
      }
    }

    setLoading(true);
    setError('');

    const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';

    try {
      const resp = await apiCall(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          password: password
        })
      });

      const data = await resp.json();
      if (resp.ok) {
        onLoginSuccess(data.token, data.username);
      } else {
        setError(data.error || (isRegister ? '注册失败' : '登录失败'));
      }
    } catch (err) {
      setError('网络连接错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-[#05050e] overflow-hidden">
      {/* Background radial ambient glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-blue-900/10 blur-[130px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-900/10 blur-[130px]" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-md p-8 glass-panel rounded-3xl shadow-[0_25px_50px_-12px_rgba(0,0,0,0.6)] flex flex-col items-center"
      >
        {/* Futuristic glowing logo */}
        <div className="relative mb-6 p-4 rounded-xl bg-gradient-to-b from-blue-500/10 to-indigo-500/5 border border-blue-500/20 shadow-[0_0_30px_rgba(59,130,246,0.1)]">
          <ShieldCheck className="w-10 h-10 text-blue-400" />
          <div className="absolute -inset-1 rounded-xl bg-blue-500/10 blur-sm -z-10 animate-pulse" />
        </div>

        <h2 className="text-2xl font-bold font-sans tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-cyan-300 mb-2">
          3hmind 统一智能体
        </h2>
        <p className="text-xs text-white/50 font-mono tracking-widest uppercase mb-8">
          SELF-ELEVATION COGNITIVE PORTAL
        </p>

        <form onSubmit={handleSubmit} className="w-full space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs text-white/40 font-medium tracking-wider">用户名</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30">
                <User className="w-4.5 h-4.5" />
              </span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={isRegister ? "用户名 (至少2个字符)" : "请输入用户名"}
                className="w-full pl-11 pr-4 py-3 text-sm rounded-xl glass-input text-white outline-none placeholder:text-white/20"
                autoComplete="username"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-white/40 font-medium tracking-wider">密码</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30">
                <Lock className="w-4.5 h-4.5" />
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="密码"
                className="w-full pl-11 pr-4 py-3 text-sm rounded-xl glass-input text-white outline-none placeholder:text-white/20"
                autoComplete={isRegister ? "new-password" : "current-password"}
              />
            </div>
          </div>

          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-start gap-2 text-xs text-rose-400 border border-rose-500/20 p-3 rounded-xl bg-rose-500/5"
              >
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-rose-400" />
                <span>{error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 mt-2 bg-gradient-to-r from-indigo-500 to-blue-600 hover:from-indigo-600 hover:to-blue-700 active:scale-[0.99] rounded-xl text-sm font-semibold text-white shadow-lg border border-white/10 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : isRegister ? (
              <>
                <UserPlus className="w-4 h-4" />
                <span>立即注册成长账号</span>
              </>
            ) : (
              <>
                <LogIn className="w-4 h-4" />
                <span>授权并登录控制台</span>
              </>
            )}
          </button>
        </form>

        <div className="mt-6 flex flex-col items-center gap-4">
          <button
            onClick={() => {
              setIsRegister(!isRegister);
              setError('');
            }}
            className="text-xs text-white/50 hover:text-blue-400 transition-colors duration-200 flex items-center gap-1.5 font-medium cursor-pointer"
          >
            {isRegister ? (
              <>
                <LogIn className="w-3.5 h-3.5" />
                <span>已有账号？返回登录</span>
              </>
            ) : (
              <>
                <UserPlus className="w-3.5 h-3.5" />
                <span>还没有账号？创建新凭证</span>
              </>
            )}
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </motion.div>
    </div>
  );
}
