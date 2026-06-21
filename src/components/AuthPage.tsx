import { useState } from 'react';
import { motion } from 'framer-motion';
import { BookOpen, Mail, Lock, User, Eye, EyeOff } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';

export default function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { isDark, loginUser, registerUser, setPage } = useStore();
  const { t, isRTL } = useTranslation();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (mode === 'login') {
      const ok = loginUser(email, password);
      if (ok) {
        setPage('home');
      } else {
        setError(isRTL ? 'البريد الإلكتروني أو كلمة المرور غير صحيحة' : 'Invalid email or password');
      }
    } else {
      if (password.length < 6) {
        setError(isRTL ? 'كلمة المرور يجب أن تكون 6 أحرف على الأقل' : 'Password must be at least 6 characters');
        return;
      }
      const ok = registerUser(name, email, password);
      if (ok) {
        setPage('home');
      } else {
        setError(isRTL ? 'البريد الإلكتروني مسجل مسبقاً' : 'Email already registered');
      }
    }
  };

  const inputClass = `w-full px-4 py-3 rounded-xl border outline-none transition-colors ${
    isDark
      ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500 focus:border-amber-500'
      : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400 focus:border-amber-500'
  }`;

  return (
    <div className={`min-h-screen flex items-center justify-center px-4 ${isDark ? 'bg-gray-950' : 'bg-gray-50'}`}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`w-full max-w-md p-8 rounded-2xl ${
          isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white shadow-xl'
        }`}
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 flex items-center justify-center rounded-2xl bg-amber-500/10">
            <BookOpen className="w-8 h-8 text-amber-500" />
          </div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {mode === 'login' ? t('loginTitle') : t('registerTitle')}
          </h1>
        </div>

        {/* Admin Hint */}
        {mode === 'login' && (
          <div className={`mb-6 p-3 rounded-xl text-xs ${isDark ? 'bg-amber-500/10 text-amber-400' : 'bg-amber-50 text-amber-700'}`}>
            <p className="font-semibold mb-1">🔑 Admin: admin@kitab.com / admin123</p>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 text-red-500 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" dir={isRTL ? 'rtl' : 'ltr'}>
          {mode === 'register' && (
            <div className="relative">
              <User className={`absolute top-3.5 ${isRTL ? 'right-4' : 'left-4'} w-5 h-5 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
              <input
                type="text"
                placeholder={t('fullName')}
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className={`${inputClass} ${isRTL ? 'pr-12' : 'pl-12'}`}
              />
            </div>
          )}

          <div className="relative">
            <Mail className={`absolute top-3.5 ${isRTL ? 'right-4' : 'left-4'} w-5 h-5 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
            <input
              type="email"
              placeholder={t('email')}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={`${inputClass} ${isRTL ? 'pr-12' : 'pl-12'}`}
            />
          </div>

          <div className="relative">
            <Lock className={`absolute top-3.5 ${isRTL ? 'right-4' : 'left-4'} w-5 h-5 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
            <input
              type={showPass ? 'text' : 'password'}
              placeholder={t('password')}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={`${inputClass} ${isRTL ? 'pr-12 pl-12' : 'pl-12 pr-12'}`}
            />
            <button
              type="button"
              onClick={() => setShowPass(!showPass)}
              className={`absolute top-3.5 ${isRTL ? 'left-4' : 'right-4'} ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
            >
              {showPass ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>

          <motion.button
            whileTap={{ scale: 0.98 }}
            type="submit"
            className="w-full py-3.5 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl transition-colors"
          >
            {mode === 'login' ? t('login') : t('register')}
          </motion.button>
        </form>

        <p className={`text-center text-sm mt-6 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          {mode === 'login' ? t('noAccount') : t('hasAccount')}{' '}
          <button
            onClick={() => setPage(mode === 'login' ? 'register' : 'login')}
            className="text-amber-500 font-semibold hover:underline"
          >
            {mode === 'login' ? t('register') : t('login')}
          </button>
        </p>
      </motion.div>
    </div>
  );
}
