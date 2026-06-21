import { motion } from 'framer-motion';
import { BookOpen, Tablet, Headphones, GraduationCap, Baby, Globe } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';
import { categoryImages } from '../data/books';
import type { BookCategory } from '../data/books';

const categoryIcons: Record<BookCategory, typeof BookOpen> = {
  paperback: BookOpen,
  ebook: Tablet,
  audiobook: Headphones,
  academic: GraduationCap,
  children: Baby,
  worldLiterature: Globe,
};

export default function Categories() {
  const { isDark, setCategory, setPage } = useStore();
  const { t } = useTranslation();

  const cats: { key: BookCategory; label: string }[] = [
    { key: 'paperback', label: t('paperback') },
    { key: 'ebook', label: t('ebook') },
    { key: 'audiobook', label: t('audiobook') },
    { key: 'academic', label: t('academic') },
    { key: 'children', label: t('children') },
    { key: 'worldLiterature', label: t('worldLiterature') },
  ];

  return (
    <section className={`py-20 ${isDark ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className={`text-3xl sm:text-4xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {t('categoriesTitle')}
          </h2>
          <p className={`text-lg ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {t('categoriesSubtitle')}
          </p>
        </motion.div>

        {/* Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {cats.map((cat, i) => {
            const Icon = categoryIcons[cat.key];
            return (
              <motion.button
                key={cat.key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                whileHover={{ y: -8 }}
                onClick={() => { setCategory(cat.key); setPage('books'); }}
                className={`group relative overflow-hidden rounded-2xl aspect-[3/4] ${
                  isDark ? 'ring-1 ring-gray-700' : 'ring-1 ring-gray-200'
                }`}
              >
                <img
                  src={categoryImages[cat.key]}
                  alt={cat.label}
                  className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent" />
                <div className="absolute bottom-0 left-0 right-0 p-4 text-center">
                  <div className="w-12 h-12 mx-auto mb-2 flex items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <p className="text-white font-semibold text-sm">{cat.label}</p>
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
