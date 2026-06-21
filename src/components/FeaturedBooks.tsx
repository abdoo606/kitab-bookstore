import { motion } from 'framer-motion';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';
import BookCard from './BookCard';

export default function FeaturedBooks() {
  const { isDark, setPage, books } = useStore();
  const { t } = useTranslation();

  const featured = books.filter((b) => b.isFeatured).slice(0, 8);

  return (
    <section className={`py-20 ${isDark ? 'bg-gray-950' : 'bg-white'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="flex items-center justify-between mb-12"
        >
          <div>
            <h2 className={`text-3xl sm:text-4xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {t('featuredBooks')}
            </h2>
            <p className={`text-lg ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('bestSellers')}
            </p>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setPage('books')}
            className={`hidden sm:block px-6 py-2.5 rounded-xl text-sm font-semibold border-2 transition-colors ${
              isDark
                ? 'border-gray-700 text-gray-300 hover:bg-gray-800'
                : 'border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {t('viewAll')}
          </motion.button>
        </motion.div>

        {/* Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
          {featured.map((book, i) => (
            <BookCard key={book.id} book={book} index={i} />
          ))}
        </div>

        {/* Mobile View All */}
        <div className="mt-8 text-center sm:hidden">
          <button
            onClick={() => setPage('books')}
            className="px-8 py-3 bg-amber-500 text-white font-semibold rounded-xl"
          >
            {t('viewAll')}
          </button>
        </div>
      </div>
    </section>
  );
}
