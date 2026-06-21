import { motion } from 'framer-motion';
import { BookOpen, Tablet, Headphones, GraduationCap, Baby, Globe, Grid3X3, LayoutList } from 'lucide-react';
import { useState } from 'react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';
import BookCard from './BookCard';
import type { BookCategory } from '../data/books';

const categoryIcons: Record<string, typeof BookOpen> = {
  all: Grid3X3,
  paperback: BookOpen,
  ebook: Tablet,
  audiobook: Headphones,
  academic: GraduationCap,
  children: Baby,
  worldLiterature: Globe,
};

export default function BooksPage() {
  const { isDark, selectedCategory, setCategory, searchQuery, books } = useStore();
  const { t } = useTranslation();
  const [sortBy, setSortBy] = useState<'default' | 'priceLow' | 'priceHigh' | 'rating'>('default');

  const categories: { key: BookCategory | 'all'; label: string }[] = [
    { key: 'all', label: t('allBooks') },
    { key: 'paperback', label: t('paperback') },
    { key: 'ebook', label: t('ebook') },
    { key: 'audiobook', label: t('audiobook') },
    { key: 'academic', label: t('academic') },
    { key: 'children', label: t('children') },
    { key: 'worldLiterature', label: t('worldLiterature') },
  ];

  let filteredBooks = selectedCategory === 'all'
    ? books
    : books.filter((b) => b.category === selectedCategory);

  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase();
    filteredBooks = filteredBooks.filter(
      (b) =>
        b.title.toLowerCase().includes(q) ||
        b.titleAr.includes(q) ||
        b.titleFr.toLowerCase().includes(q) ||
        b.author.toLowerCase().includes(q) ||
        b.authorAr.includes(q)
    );
  }

  if (sortBy === 'priceLow') filteredBooks = [...filteredBooks].sort((a, b) => a.price - b.price);
  if (sortBy === 'priceHigh') filteredBooks = [...filteredBooks].sort((a, b) => b.price - a.price);
  if (sortBy === 'rating') filteredBooks = [...filteredBooks].sort((a, b) => b.rating - a.rating);

  return (
    <div className={`min-h-screen pt-24 pb-16 ${isDark ? 'bg-gray-950' : 'bg-gray-50'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className={`text-3xl sm:text-4xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {t('books')}
          </h1>
          <p className={`text-lg ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {filteredBooks.length} {t('books')}
          </p>
        </motion.div>

        {/* Category Filters */}
        <div className="flex flex-wrap gap-2 mb-8">
          {categories.map((cat) => {
            const Icon = categoryIcons[cat.key];
            return (
              <motion.button
                key={cat.key}
                whileTap={{ scale: 0.95 }}
                onClick={() => setCategory(cat.key)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  selectedCategory === cat.key
                    ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/25'
                    : isDark
                      ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                      : 'bg-white text-gray-600 hover:bg-gray-100 ring-1 ring-gray-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                {cat.label}
              </motion.button>
            );
          })}
        </div>

        {/* Sort */}
        <div className="flex items-center justify-between mb-6">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className={`px-4 py-2 rounded-xl text-sm border outline-none ${
              isDark
                ? 'bg-gray-800 border-gray-700 text-gray-300'
                : 'bg-white border-gray-200 text-gray-700'
            }`}
          >
            <option value="default">{t('featuredBooks')}</option>
            <option value="priceLow">{t('price')} ↑</option>
            <option value="priceHigh">{t('price')} ↓</option>
            <option value="rating">{t('rating')} ↓</option>
          </select>
        </div>

        {/* Products Grid */}
        {filteredBooks.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
            {filteredBooks.map((book, i) => (
              <BookCard key={book.id} book={book} index={i} />
            ))}
          </div>
        ) : (
          <div className="text-center py-20">
            <LayoutList className={`w-16 h-16 mx-auto mb-4 ${isDark ? 'text-gray-600' : 'text-gray-300'}`} />
            <p className={`text-xl font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              {t('noResults')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
