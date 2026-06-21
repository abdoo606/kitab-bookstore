import { motion, AnimatePresence } from 'framer-motion';
import { X, Star, ShoppingCart, Download, Headphones } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';

export default function BookModal() {
  const { isDark, selectedBook, setSelectedBook, addToCart, language } = useStore();
  const { t, formatPrice } = useTranslation();

  if (!selectedBook) return null;

  const book = selectedBook;
  const title = language === 'ar' ? book.titleAr : language === 'fr' ? book.titleFr : book.title;
  const author = language === 'ar' ? book.authorAr : language === 'fr' ? book.authorFr : book.author;
  const desc = language === 'ar' ? book.descriptionAr : language === 'fr' ? book.descriptionFr : book.description;

  return (
    <AnimatePresence>
      {selectedBook && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedBook(null)}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className={`fixed inset-4 sm:inset-auto sm:left-1/2 sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 z-50 w-auto sm:w-full sm:max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl ${
              isDark ? 'bg-gray-900' : 'bg-white'
            } shadow-2xl`}
          >
            {/* Close */}
            <button
              onClick={() => setSelectedBook(null)}
              className={`absolute top-4 right-4 z-10 p-2 rounded-full ${
                isDark ? 'bg-gray-800 text-gray-400 hover:bg-gray-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              <X className="w-5 h-5" />
            </button>

            <div className="sm:flex">
              {/* Image */}
              <div className="sm:w-2/5">
                <img
                  src={book.image}
                  alt={title}
                  className="w-full h-64 sm:h-full object-cover sm:rounded-l-2xl"
                />
              </div>

              {/* Details */}
              <div className="sm:w-3/5 p-6 sm:p-8">
                <p className={`text-sm font-medium mb-2 ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                  {t(book.category)}
                </p>
                <h2 className={`text-2xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {title}
                </h2>
                <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  {t('author')}: {author}
                </p>

                {/* Rating */}
                <div className="flex items-center gap-2 mb-4">
                  <div className="flex">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star
                        key={star}
                        className={`w-4 h-4 ${
                          star <= Math.round(book.rating)
                            ? 'fill-amber-400 text-amber-400'
                            : isDark ? 'text-gray-600' : 'text-gray-300'
                        }`}
                      />
                    ))}
                  </div>
                  <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    {book.rating} ({book.reviews} {t('reviews')})
                  </span>
                </div>

                {/* Price */}
                <div className="flex items-center gap-3 mb-6">
                  <span className={`text-3xl font-bold ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                    {formatPrice(book.price)}
                  </span>
                  {book.originalPrice && (
                    <span className={`text-lg line-through ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      {formatPrice(book.originalPrice)}
                    </span>
                  )}
                </div>

                {/* Description */}
                <p className={`text-sm leading-relaxed mb-6 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                  {desc}
                </p>

                {/* Details Grid */}
                <div className={`grid grid-cols-2 gap-3 mb-6 p-4 rounded-xl ${
                  isDark ? 'bg-gray-800' : 'bg-gray-50'
                }`}>
                  {book.pages && (
                    <div>
                      <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{t('pages')}</p>
                      <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{book.pages}</p>
                    </div>
                  )}
                  <div>
                    <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{t('format')}</p>
                    <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{book.format}</p>
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{t('publisher')}</p>
                    <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{book.publisher}</p>
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{t('isbn')}</p>
                    <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{book.isbn}</p>
                  </div>
                </div>

                {/* Add to Cart */}
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  onClick={() => { addToCart(book); setSelectedBook(null); }}
                  className="w-full py-3.5 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-colors"
                >
                  {book.category === 'ebook' ? (
                    <><Download className="w-5 h-5" /> {t('downloadNow')}</>
                  ) : book.category === 'audiobook' ? (
                    <><Headphones className="w-5 h-5" /> {t('listenNow')}</>
                  ) : (
                    <><ShoppingCart className="w-5 h-5" /> {t('addToCart')}</>
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
