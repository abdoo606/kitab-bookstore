import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, ArrowLeft, BookOpen, Headphones, Tablet } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';

const HERO_IMAGES = [
  'https://images.pexels.com/photos/159711/books-bookstore-book-reading-159711.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1080&fit=crop',
  'https://images.pexels.com/photos/256541/pexels-photo-256541.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1080&fit=crop',
  'https://images.pexels.com/photos/1290141/pexels-photo-1290141.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1080&fit=crop',
];

export default function Hero() {
  const { isDark, setPage, setCategory } = useStore();
  const { t, isRTL } = useTranslation();
  const [imgIndex, setImgIndex] = useState(0);
  const [imgLoaded, setImgLoaded] = useState(false);

  const Arrow = isRTL ? ArrowLeft : ArrowRight;

  const handleImgError = () => {
    if (imgIndex < HERO_IMAGES.length - 1) {
      setImgIndex(imgIndex + 1);
    }
  };

  return (
    <section className="relative min-h-screen flex items-center overflow-hidden">
      {/* Fallback gradient background (always visible behind image) */}
      <div className={`absolute inset-0 ${
        isDark
          ? 'bg-gradient-to-br from-gray-900 via-amber-950/30 to-gray-950'
          : 'bg-gradient-to-br from-amber-50 via-orange-50 to-white'
      }`} />

      {/* Background Image */}
      <div className="absolute inset-0">
        <img
          src={HERO_IMAGES[imgIndex]}
          alt="Library"
          className={`w-full h-full object-cover transition-opacity duration-700 ${imgLoaded ? 'opacity-100' : 'opacity-0'}`}
          loading="eager"
          onLoad={() => setImgLoaded(true)}
          onError={handleImgError}
        />
        <div className={`absolute inset-0 ${
          isDark
            ? 'bg-gradient-to-r from-gray-900/95 via-gray-900/85 to-gray-900/60'
            : 'bg-gradient-to-r from-white/95 via-white/85 to-white/40'
        }`} />
      </div>

      {/* Decorative Elements */}
      <div className={`absolute top-20 ${isRTL ? 'left-10' : 'right-10'} w-96 h-96 rounded-full blur-3xl ${
        isDark ? 'bg-amber-500/5' : 'bg-amber-200/20'
      }`} />
      <div className={`absolute bottom-10 ${isRTL ? 'right-20' : 'left-20'} w-64 h-64 rounded-full blur-3xl ${
        isDark ? 'bg-amber-600/5' : 'bg-orange-200/20'
      }`} />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-32">
        <div className="max-w-2xl">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium mb-6 ${
              isDark ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>📚 KITAB — Premium Bookstore</span>
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className={`text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6 ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}
          >
            {t('heroTitle')}
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className={`text-lg sm:text-xl mb-8 leading-relaxed ${
              isDark ? 'text-gray-300' : 'text-gray-600'
            }`}
          >
            {t('heroSubtitle')}
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            className="flex flex-wrap gap-4 mb-12"
          >
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setPage('books')}
              className="flex items-center gap-2 px-8 py-4 bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl transition-colors shadow-lg shadow-amber-500/25"
            >
              {t('shopNow')}
              <Arrow className="w-5 h-5" />
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => { setCategory('all'); setPage('books'); }}
              className={`flex items-center gap-2 px-8 py-4 font-semibold rounded-xl border-2 transition-colors ${
                isDark
                  ? 'border-gray-600 text-white hover:bg-gray-800'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              {t('exploreCatalog')}
            </motion.button>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1 }}
            className="flex flex-wrap gap-6 sm:gap-8"
          >
            {[
              { icon: BookOpen, label: isRTL ? 'كتب ورقية' : 'Paperbacks', count: '5,000+' },
              { icon: Tablet, label: isRTL ? 'كتب رقمية' : 'E-Books', count: '10,000+' },
              { icon: Headphones, label: isRTL ? 'كتب صوتية' : 'Audiobooks', count: '3,000+' },
            ].map((stat, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className={`w-12 h-12 flex items-center justify-center rounded-xl backdrop-blur-sm ${
                  isDark ? 'bg-gray-800/80' : 'bg-white/80 shadow-sm'
                }`}>
                  <stat.icon className={`w-6 h-6 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
                </div>
                <div>
                  <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{stat.count}</p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{stat.label}</p>
                </div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
