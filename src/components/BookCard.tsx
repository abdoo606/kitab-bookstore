import { motion } from 'framer-motion';
import { ShoppingCart, Eye, Star, Download, Headphones } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';
import type { Book } from '../data/books';

interface BookCardProps {
  book: Book;
  index?: number;
}

export default function BookCard({ book, index = 0 }: BookCardProps) {
  const { isDark, addToCart, setSelectedBook, language } = useStore();
  const { t, formatPrice } = useTranslation();

  const title = language === 'ar' ? book.titleAr : language === 'fr' ? book.titleFr : book.title;
  const author = language === 'ar' ? book.authorAr : language === 'fr' ? book.authorFr : book.author;

  const isDigital = book.category === 'ebook' || book.category === 'audiobook';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.05 }}
      className={`group relative rounded-2xl overflow-hidden transition-all duration-300 ${
        isDark
          ? 'bg-gray-800 hover:bg-gray-750 ring-1 ring-gray-700'
          : 'bg-white hover:shadow-xl ring-1 ring-gray-100'
      }`}
    >
      {/* Image */}
      <div className="relative aspect-[3/4] overflow-hidden">
        <img
          src={book.image}
          alt={title}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        />
        
        {/* Overlay */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all duration-300 flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100">
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => addToCart(book)}
            className="w-12 h-12 flex items-center justify-center rounded-full bg-amber-500 text-white shadow-lg"
          >
            <ShoppingCart className="w-5 h-5" />
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => setSelectedBook(book)}
            className="w-12 h-12 flex items-center justify-center rounded-full bg-white text-gray-900 shadow-lg"
          >
            <Eye className="w-5 h-5" />
          </motion.button>
        </div>

        {/* Badges */}
        <div className="absolute top-3 left-3 right-3 flex justify-between">
          <div className="flex flex-col gap-1.5">
            {book.isNew && (
              <span className="px-2.5 py-1 text-[10px] font-bold uppercase bg-emerald-500 text-white rounded-lg">
                {language === 'ar' ? 'جديد' : 'New'}
              </span>
            )}
            {book.isBestSeller && (
              <span className="px-2.5 py-1 text-[10px] font-bold uppercase bg-amber-500 text-white rounded-lg">
                {language === 'ar' ? 'الأكثر مبيعاً' : 'Best Seller'}
              </span>
            )}
            {isDigital && (
              <span className="px-2.5 py-1 text-[10px] font-bold uppercase bg-blue-500 text-white rounded-lg flex items-center gap-1">
                {book.category === 'audiobook' ? <Headphones className="w-3 h-3" /> : <Download className="w-3 h-3" />}
                {t('digital')}
              </span>
            )}
          </div>
          {book.originalPrice && (
            <span className="px-2.5 py-1 text-[10px] font-bold bg-red-500 text-white rounded-lg h-fit">
              -{Math.round((1 - book.price / book.originalPrice) * 100)}%
            </span>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="p-4">
        {/* Category */}
        <p className={`text-xs font-medium mb-1 ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
          {t(book.category)}
        </p>

        {/* Title */}
        <h3 className={`font-semibold text-sm line-clamp-2 mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          {title}
        </h3>

        {/* Author */}
        <p className={`text-xs mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          {author}
        </p>

        {/* Rating */}
        <div className="flex items-center gap-1 mb-3">
          <div className="flex">
            {[1, 2, 3, 4, 5].map((star) => (
              <Star
                key={star}
                className={`w-3.5 h-3.5 ${
                  star <= Math.round(book.rating)
                    ? 'fill-amber-400 text-amber-400'
                    : isDark ? 'text-gray-600' : 'text-gray-300'
                }`}
              />
            ))}
          </div>
          <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            ({book.reviews})
          </span>
        </div>

        {/* Price */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`font-bold text-lg ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
              {formatPrice(book.price)}
            </span>
            {book.originalPrice && (
              <span className={`text-sm line-through ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                {formatPrice(book.originalPrice)}
              </span>
            )}
          </div>
        </div>

        {/* Quick Add */}
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={() => addToCart(book)}
          className={`w-full mt-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
            isDark
              ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
              : 'bg-amber-50 text-amber-600 hover:bg-amber-100'
          }`}
        >
          {book.category === 'ebook' ? t('downloadNow') :
           book.category === 'audiobook' ? t('listenNow') :
           t('addToCart')}
        </motion.button>
      </div>
    </motion.div>
  );
}
