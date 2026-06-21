import { motion } from 'framer-motion';
import { Sparkles, Clock, TrendingUp, Star, Flame } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';
import BookCard from './BookCard';

export default function NewArrivalsPage() {
  const { isDark, books } = useStore();
  const { t, isRTL } = useTranslation();

  // Books marked as new or the most recently added
  const newBooks = books.filter((b) => b.isNew);
  const recentBooks = books.slice(-6).reverse();
  const allNewArrivals = [...new Map([...newBooks, ...recentBooks].map(b => [b.id, b])).values()];

  return (
    <div className={`min-h-screen pt-20 pb-16 ${isDark ? 'bg-gray-950' : 'bg-gray-50'}`}>
      {/* Hero Banner */}
      <div className="relative overflow-hidden">
        <div className={`absolute inset-0 ${
          isDark 
            ? 'bg-gradient-to-br from-emerald-950 via-gray-950 to-teal-950' 
            : 'bg-gradient-to-br from-emerald-50 via-white to-teal-50'
        }`} />
        {/* Decorative circles */}
        <div className={`absolute top-10 ${isRTL ? 'left-10' : 'right-10'} w-72 h-72 rounded-full blur-3xl ${
          isDark ? 'bg-emerald-500/10' : 'bg-emerald-200/40'
        }`} />
        <div className={`absolute bottom-0 ${isRTL ? 'right-20' : 'left-20'} w-48 h-48 rounded-full blur-3xl ${
          isDark ? 'bg-teal-500/10' : 'bg-teal-200/30'
        }`} />

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium mb-6 ${
                isDark ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-emerald-100 text-emerald-700 border border-emerald-200'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              {t('justLanded')}
            </motion.div>

            <h1 className={`text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-4 ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>
              {t('newArrivalsTitle')}
              <span className={`block text-transparent bg-clip-text bg-gradient-to-r ${
                isDark ? 'from-emerald-400 to-teal-400' : 'from-emerald-600 to-teal-600'
              }`}>
                {t('thisWeek')} ✨
              </span>
            </h1>

            <p className={`text-lg sm:text-xl leading-relaxed ${
              isDark ? 'text-gray-400' : 'text-gray-600'
            }`}>
              {t('newArrivalsSubtitle')}
            </p>
          </motion.div>

          {/* Quick Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="flex flex-wrap gap-6 mt-10"
          >
            {[
              { icon: Clock, value: allNewArrivals.length.toString(), label: isRTL ? 'كتاب جديد' : 'New Books' },
              { icon: TrendingUp, value: '24h', label: isRTL ? 'تحديث مستمر' : 'Updated Daily' },
              { icon: Flame, value: '🔥', label: isRTL ? 'الأكثر طلباً' : 'Trending Now' },
            ].map((stat, i) => (
              <div key={i} className={`flex items-center gap-3 px-5 py-3 rounded-2xl ${
                isDark ? 'bg-gray-800/80 backdrop-blur-sm' : 'bg-white/80 backdrop-blur-sm shadow-sm'
              }`}>
                <div className={`w-10 h-10 flex items-center justify-center rounded-xl ${
                  isDark ? 'bg-emerald-500/20' : 'bg-emerald-100'
                }`}>
                  {stat.value === '🔥' ? (
                    <span className="text-lg">{stat.value}</span>
                  ) : (
                    <stat.icon className={`w-5 h-5 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`} />
                  )}
                </div>
                <div>
                  {stat.value !== '🔥' && (
                    <p className={`text-lg font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{stat.value}</p>
                  )}
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{stat.label}</p>
                </div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>

      {/* Books Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        {allNewArrivals.length > 0 ? (
          <>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="flex items-center gap-3 mb-8"
            >
              <div className={`w-10 h-10 flex items-center justify-center rounded-xl ${
                isDark ? 'bg-emerald-500/20' : 'bg-emerald-100'
              }`}>
                <Star className={`w-5 h-5 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`} />
              </div>
              <div>
                <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {t('newArrivalsTitle')}
                </h2>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  {allNewArrivals.length} {t('books')}
                </p>
              </div>
            </motion.div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
              {allNewArrivals.map((book, i) => (
                <BookCard key={book.id} book={book} index={i} />
              ))}
            </div>
          </>
        ) : (
          <div className="text-center py-20">
            <Sparkles className={`w-16 h-16 mx-auto mb-4 ${isDark ? 'text-gray-600' : 'text-gray-300'}`} />
            <p className={`text-xl font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              {t('noResults')}
            </p>
          </div>
        )}

        {/* Promotional Strip */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className={`mt-16 p-8 sm:p-12 rounded-3xl relative overflow-hidden ${
            isDark ? 'bg-gradient-to-r from-emerald-900/50 to-teal-900/50 ring-1 ring-emerald-500/20' : 'bg-gradient-to-r from-emerald-50 to-teal-50 ring-1 ring-emerald-200'
          }`}
        >
          <div className={`absolute top-0 ${isRTL ? 'left-0' : 'right-0'} w-64 h-64 rounded-full blur-3xl ${
            isDark ? 'bg-emerald-500/10' : 'bg-emerald-200/40'
          }`} />
          <div className="relative z-10 flex flex-col sm:flex-row items-center justify-between gap-6">
            <div>
              <h3 className={`text-2xl sm:text-3xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                📬 {isRTL ? 'لا تفوّت أي إصدار جديد!' : "Don't Miss Any New Release!"}
              </h3>
              <p className={`${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                {isRTL ? 'اشترك بالنشرة البريدية لتصلك أحدث الكتب أولاً' : 'Subscribe to our newsletter and be the first to know'}
              </p>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <input
                type="email"
                placeholder={t('enterEmail')}
                className={`flex-1 sm:w-64 px-4 py-3 rounded-xl text-sm border outline-none ${
                  isDark ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500' : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400'
                }`}
              />
              <button className="px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl text-sm transition-colors whitespace-nowrap">
                {t('subscribe')}
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
