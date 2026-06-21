import { motion } from 'framer-motion';
import { Percent, Timer, Zap, Gift, Tag, ShoppingCart, Star, ArrowRight, ArrowLeft, Flame } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';
import BookCard from './BookCard';
import { useState, useEffect } from 'react';

function CountdownTimer({ isDark }: { isDark: boolean }) {
  const [time, setTime] = useState({ hours: 23, minutes: 45, seconds: 30 });

  useEffect(() => {
    const interval = setInterval(() => {
      setTime((prev) => {
        let { hours, minutes, seconds } = prev;
        seconds--;
        if (seconds < 0) { seconds = 59; minutes--; }
        if (minutes < 0) { minutes = 59; hours--; }
        if (hours < 0) { hours = 23; minutes = 59; seconds = 59; }
        return { hours, minutes, seconds };
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const pad = (n: number) => n.toString().padStart(2, '0');

  return (
    <div className="flex items-center gap-2">
      {[
        { value: pad(time.hours), label: 'H' },
        { value: pad(time.minutes), label: 'M' },
        { value: pad(time.seconds), label: 'S' },
      ].map((unit, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className={`px-3 py-2 rounded-xl text-center min-w-[48px] ${
            isDark ? 'bg-red-500/20 text-red-400' : 'bg-red-100 text-red-600'
          }`}>
            <p className="text-xl font-bold font-mono">{unit.value}</p>
            <p className="text-[10px] uppercase opacity-70">{unit.label}</p>
          </div>
          {i < 2 && <span className={`text-2xl font-bold ${isDark ? 'text-red-400' : 'text-red-500'}`}>:</span>}
        </div>
      ))}
    </div>
  );
}

export default function OffersPage() {
  const { isDark, books, addToCart, setPage, language } = useStore();
  const { t, formatPrice, isRTL } = useTranslation();

  const Arrow = isRTL ? ArrowLeft : ArrowRight;

  // Books with discount (originalPrice exists)
  const discountedBooks = books.filter((b) => b.originalPrice && b.originalPrice > b.price);

  // Top deal (biggest discount)
  const topDeal = discountedBooks.length > 0
    ? discountedBooks.reduce((best, b) => {
        const bestDiscount = best.originalPrice ? (1 - best.price / best.originalPrice) : 0;
        const currentDiscount = b.originalPrice ? (1 - b.price / b.originalPrice) : 0;
        return currentDiscount > bestDiscount ? b : best;
      })
    : null;

  const otherDeals = discountedBooks.filter((b) => b.id !== topDeal?.id);

  const getTitle = (book: typeof books[0]) => language === 'ar' ? book.titleAr : language === 'fr' ? book.titleFr : book.title;
  const getAuthor = (book: typeof books[0]) => language === 'ar' ? book.authorAr : language === 'fr' ? book.authorFr : book.author;
  const getDesc = (book: typeof books[0]) => language === 'ar' ? book.descriptionAr : language === 'fr' ? book.descriptionFr : book.description;

  return (
    <div className={`min-h-screen pt-20 pb-16 ${isDark ? 'bg-gray-950' : 'bg-gray-50'}`}>
      {/* Hero Banner */}
      <div className="relative overflow-hidden">
        <div className={`absolute inset-0 ${
          isDark 
            ? 'bg-gradient-to-br from-red-950 via-gray-950 to-orange-950' 
            : 'bg-gradient-to-br from-red-50 via-white to-orange-50'
        }`} />
        {/* Decorative */}
        <div className={`absolute top-5 ${isRTL ? 'left-10' : 'right-10'} w-80 h-80 rounded-full blur-3xl ${
          isDark ? 'bg-red-500/8' : 'bg-red-200/30'
        }`} />
        <div className={`absolute bottom-0 ${isRTL ? 'right-20' : 'left-20'} w-60 h-60 rounded-full blur-3xl ${
          isDark ? 'bg-orange-500/8' : 'bg-orange-200/20'
        }`} />

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-8">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-xl"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 }}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold mb-6 ${
                  isDark ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-red-100 text-red-600 border border-red-200'
                }`}
              >
                <Flame className="w-4 h-4" />
                {t('hotDeal')}
              </motion.div>

              <h1 className={`text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-4 ${
                isDark ? 'text-white' : 'text-gray-900'
              }`}>
                {t('offersTitle')}
                <span className="block">
                  <span className={`text-transparent bg-clip-text bg-gradient-to-r ${
                    isDark ? 'from-red-400 to-orange-400' : 'from-red-600 to-orange-600'
                  }`}>
                    {t('saveUpTo')} 40% 🎁
                  </span>
                </span>
              </h1>

              <p className={`text-lg leading-relaxed mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {t('offersSubtitle')}
              </p>

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setPage('books')}
                className="flex items-center gap-2 px-8 py-4 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-xl transition-colors shadow-lg shadow-red-500/25"
              >
                {t('shopNow')}
                <Arrow className="w-5 h-5" />
              </motion.button>
            </motion.div>

            {/* Countdown */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.4 }}
              className={`p-6 rounded-2xl ${
                isDark ? 'bg-gray-800/80 backdrop-blur-sm ring-1 ring-gray-700' : 'bg-white/90 backdrop-blur-sm shadow-xl'
              }`}
            >
              <div className="flex items-center gap-2 mb-4">
                <Timer className={`w-5 h-5 ${isDark ? 'text-red-400' : 'text-red-500'}`} />
                <p className={`text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  {t('limitedTime')}
                </p>
              </div>
              <CountdownTimer isDark={isDark} />
            </motion.div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {discountedBooks.length > 0 ? (
          <>
            {/* Top Deal Hero Card */}
            {topDeal && topDeal.originalPrice && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className={`-mt-8 relative z-10 mb-12 rounded-3xl overflow-hidden ${
                  isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200 shadow-xl'
                }`}
              >
                <div className="flex flex-col md:flex-row">
                  {/* Image */}
                  <div className="md:w-2/5 relative">
                    <img
                      src={topDeal.image}
                      alt={getTitle(topDeal)}
                      className="w-full h-72 md:h-full object-cover"
                    />
                    <div className="absolute top-4 left-4">
                      <span className="px-4 py-2 bg-red-500 text-white font-bold rounded-xl text-lg animate-pulse">
                        -{Math.round((1 - topDeal.price / topDeal.originalPrice) * 100)}% {t('off')}
                      </span>
                    </div>
                  </div>

                  {/* Details */}
                  <div className="md:w-3/5 p-8 sm:p-10 flex flex-col justify-center">
                    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold mb-4 w-fit ${
                      isDark ? 'bg-red-500/20 text-red-400' : 'bg-red-100 text-red-600'
                    }`}>
                      <Zap className="w-3.5 h-3.5" />
                      {t('hotDeal')}
                    </div>

                    <h2 className={`text-2xl sm:text-3xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {getTitle(topDeal)}
                    </h2>

                    <p className={`text-sm mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      {t('author')}: {getAuthor(topDeal)}
                    </p>

                    {/* Rating */}
                    <div className="flex items-center gap-2 mb-4">
                      <div className="flex">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <Star key={s} className={`w-4 h-4 ${
                            s <= Math.round(topDeal.rating) ? 'fill-amber-400 text-amber-400' : isDark ? 'text-gray-600' : 'text-gray-300'
                          }`} />
                        ))}
                      </div>
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        ({topDeal.reviews})
                      </span>
                    </div>

                    <p className={`text-sm leading-relaxed mb-6 line-clamp-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                      {getDesc(topDeal)}
                    </p>

                    {/* Prices */}
                    <div className="flex items-center gap-4 mb-6">
                      <span className={`text-4xl font-bold ${isDark ? 'text-red-400' : 'text-red-600'}`}>
                        {formatPrice(topDeal.price)}
                      </span>
                      <span className={`text-xl line-through ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                        {formatPrice(topDeal.originalPrice)}
                      </span>
                      <span className={`px-3 py-1.5 rounded-xl text-sm font-bold ${
                        isDark ? 'bg-emerald-500/20 text-emerald-400' : 'bg-emerald-100 text-emerald-600'
                      }`}>
                        {t('saveUpTo')} {formatPrice(topDeal.originalPrice - topDeal.price)}
                      </span>
                    </div>

                    <motion.button
                      whileTap={{ scale: 0.95 }}
                      onClick={() => addToCart(topDeal)}
                      className="self-start flex items-center gap-2 px-8 py-3.5 bg-red-500 hover:bg-red-600 text-white font-bold rounded-xl transition-colors"
                    >
                      <ShoppingCart className="w-5 h-5" />
                      {t('addToCart')}
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Other Deals */}
            {otherDeals.length > 0 && (
              <>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  className="flex items-center gap-3 mb-8"
                >
                  <div className={`w-10 h-10 flex items-center justify-center rounded-xl ${
                    isDark ? 'bg-red-500/20' : 'bg-red-100'
                  }`}>
                    <Tag className={`w-5 h-5 ${isDark ? 'text-red-400' : 'text-red-600'}`} />
                  </div>
                  <div>
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {isRTL ? 'عروض أخرى' : language === 'fr' ? 'Autres Offres' : 'More Deals'}
                    </h2>
                    <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      {otherDeals.length} {t('books')}
                    </p>
                  </div>
                </motion.div>

                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
                  {otherDeals.map((book, i) => (
                    <BookCard key={book.id} book={book} index={i} />
                  ))}
                </div>
              </>
            )}

            {/* CTA Banner */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className={`mt-16 p-8 sm:p-12 rounded-3xl text-center relative overflow-hidden ${
                isDark ? 'bg-gradient-to-r from-red-900/40 to-orange-900/40 ring-1 ring-red-500/20' : 'bg-gradient-to-r from-red-50 to-orange-50 ring-1 ring-red-200'
              }`}
            >
              <div className={`absolute top-0 ${isRTL ? 'left-0' : 'right-0'} w-48 h-48 rounded-full blur-3xl ${
                isDark ? 'bg-red-500/10' : 'bg-red-200/30'
              }`} />
              <div className="relative z-10">
                <Gift className={`w-12 h-12 mx-auto mb-4 ${isDark ? 'text-red-400' : 'text-red-500'}`} />
                <h3 className={`text-2xl sm:text-3xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {isRTL ? 'لا تفوّت العروض القادمة!' : language === 'fr' ? 'Ne manquez pas les prochaines offres!' : "Don't Miss Future Deals!"}
                </h3>
                <p className={`mb-6 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                  {isRTL ? 'اشترك لتصلك العروض الحصرية على بريدك' : language === 'fr' ? 'Abonnez-vous pour des offres exclusives' : 'Subscribe for exclusive offers in your inbox'}
                </p>
                <div className="flex gap-2 max-w-md mx-auto">
                  <input
                    type="email"
                    placeholder={t('enterEmail')}
                    className={`flex-1 px-4 py-3 rounded-xl text-sm border outline-none ${
                      isDark ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500' : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400'
                    }`}
                  />
                  <button className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-xl text-sm transition-colors whitespace-nowrap">
                    {t('subscribe')}
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        ) : (
          /* Empty State */
          <div className="text-center py-20">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <div className={`w-24 h-24 mx-auto mb-6 flex items-center justify-center rounded-full ${
                isDark ? 'bg-gray-800' : 'bg-gray-100'
              }`}>
                <Percent className={`w-12 h-12 ${isDark ? 'text-gray-600' : 'text-gray-300'}`} />
              </div>
              <h2 className={`text-2xl font-bold mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                {t('offersEmptyTitle')}
              </h2>
              <p className={`text-lg mb-8 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                {t('offersEmptySubtitle')}
              </p>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setPage('books')}
                className="px-8 py-3 bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl transition-colors"
              >
                {t('continueShopping')}
              </motion.button>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}
