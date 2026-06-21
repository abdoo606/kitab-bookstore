import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, Save } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';
import type { Book, BookCategory } from '../data/books';

interface BookFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  editBook?: Book | null;
}

const emptyBook: Omit<Book, 'id'> = {
  title: '',
  titleAr: '',
  titleFr: '',
  author: '',
  authorAr: '',
  authorFr: '',
  price: 0,
  originalPrice: undefined,
  category: 'paperback',
  image: 'https://images.pexels.com/photos/1050736/pexels-photo-1050736.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=600&w=400',
  rating: 4.5,
  reviews: 0,
  inStock: true,
  isNew: false,
  isBestSeller: false,
  isFeatured: false,
  pages: 200,
  description: '',
  descriptionAr: '',
  descriptionFr: '',
  isbn: '',
  publisher: '',
  year: new Date().getFullYear(),
  format: 'Paperback',
};

export default function BookFormModal({ isOpen, onClose, editBook }: BookFormModalProps) {
  const { isDark, addBook, updateBook } = useStore();
  const { t, isRTL } = useTranslation();
  
  const [form, setForm] = useState<Omit<Book, 'id'>>(emptyBook);
  const [activeTab, setActiveTab] = useState<'en' | 'ar' | 'fr'>('en');

  useEffect(() => {
    if (editBook) {
      const { id, ...rest } = editBook;
      setForm(rest);
    } else {
      setForm(emptyBook);
    }
  }, [editBook, isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editBook) {
      updateBook(editBook.id, form);
    } else {
      addBook(form);
    }
    onClose();
    setForm(emptyBook);
  };

  const categories: { key: BookCategory; label: string }[] = [
    { key: 'paperback', label: t('paperback') },
    { key: 'ebook', label: t('ebook') },
    { key: 'audiobook', label: t('audiobook') },
    { key: 'academic', label: t('academic') },
    { key: 'children', label: t('children') },
    { key: 'worldLiterature', label: t('worldLiterature') },
  ];

  const inputClass = `w-full px-4 py-3 rounded-xl border outline-none transition-colors ${
    isDark
      ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500 focus:border-amber-500'
      : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-amber-500'
  }`;

  const labelClass = `block text-sm font-medium mb-1.5 ${isDark ? 'text-gray-300' : 'text-gray-700'}`;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className={`fixed inset-4 sm:inset-auto sm:left-1/2 sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 z-50 w-auto sm:w-full sm:max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl ${
              isDark ? 'bg-gray-900' : 'bg-white'
            } shadow-2xl`}
          >
            {/* Header */}
            <div className={`sticky top-0 z-10 flex items-center justify-between p-6 border-b ${
              isDark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'
            }`}>
              <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {editBook ? t('editProduct') : t('addProduct')}
              </h2>
              <button
                onClick={onClose}
                className={`p-2 rounded-full ${isDark ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-500'}`}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6">
              {/* Language Tabs */}
              <div className="flex gap-2 mb-6">
                {[
                  { key: 'en' as const, label: '🇺🇸 English' },
                  { key: 'ar' as const, label: '🇸🇦 العربية' },
                  { key: 'fr' as const, label: '🇫🇷 Français' },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setActiveTab(tab.key)}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                      activeTab === tab.key
                        ? 'bg-amber-500 text-white'
                        : isDark ? 'bg-gray-800 text-gray-300 hover:bg-gray-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="grid lg:grid-cols-2 gap-6">
                {/* Left Column */}
                <div className="space-y-4">
                  {/* Title based on language */}
                  {activeTab === 'en' && (
                    <div>
                      <label className={labelClass}>Title (English) *</label>
                      <input
                        type="text"
                        value={form.title}
                        onChange={(e) => setForm({ ...form, title: e.target.value })}
                        required
                        placeholder="Book title in English"
                        className={inputClass}
                      />
                    </div>
                  )}
                  {activeTab === 'ar' && (
                    <div>
                      <label className={labelClass}>العنوان (عربي) *</label>
                      <input
                        type="text"
                        value={form.titleAr}
                        onChange={(e) => setForm({ ...form, titleAr: e.target.value })}
                        required
                        placeholder="عنوان الكتاب بالعربي"
                        className={inputClass}
                        dir="rtl"
                      />
                    </div>
                  )}
                  {activeTab === 'fr' && (
                    <div>
                      <label className={labelClass}>Titre (Français) *</label>
                      <input
                        type="text"
                        value={form.titleFr}
                        onChange={(e) => setForm({ ...form, titleFr: e.target.value })}
                        required
                        placeholder="Titre du livre en français"
                        className={inputClass}
                      />
                    </div>
                  )}

                  {/* Author based on language */}
                  {activeTab === 'en' && (
                    <div>
                      <label className={labelClass}>Author (English) *</label>
                      <input
                        type="text"
                        value={form.author}
                        onChange={(e) => setForm({ ...form, author: e.target.value })}
                        required
                        placeholder="Author name"
                        className={inputClass}
                      />
                    </div>
                  )}
                  {activeTab === 'ar' && (
                    <div>
                      <label className={labelClass}>المؤلف (عربي) *</label>
                      <input
                        type="text"
                        value={form.authorAr}
                        onChange={(e) => setForm({ ...form, authorAr: e.target.value })}
                        required
                        placeholder="اسم المؤلف"
                        className={inputClass}
                        dir="rtl"
                      />
                    </div>
                  )}
                  {activeTab === 'fr' && (
                    <div>
                      <label className={labelClass}>Auteur (Français) *</label>
                      <input
                        type="text"
                        value={form.authorFr}
                        onChange={(e) => setForm({ ...form, authorFr: e.target.value })}
                        required
                        placeholder="Nom de l'auteur"
                        className={inputClass}
                      />
                    </div>
                  )}

                  {/* Description based on language */}
                  {activeTab === 'en' && (
                    <div>
                      <label className={labelClass}>Description (English)</label>
                      <textarea
                        value={form.description}
                        onChange={(e) => setForm({ ...form, description: e.target.value })}
                        placeholder="Book description..."
                        rows={4}
                        className={inputClass}
                      />
                    </div>
                  )}
                  {activeTab === 'ar' && (
                    <div>
                      <label className={labelClass}>الوصف (عربي)</label>
                      <textarea
                        value={form.descriptionAr}
                        onChange={(e) => setForm({ ...form, descriptionAr: e.target.value })}
                        placeholder="وصف الكتاب..."
                        rows={4}
                        className={inputClass}
                        dir="rtl"
                      />
                    </div>
                  )}
                  {activeTab === 'fr' && (
                    <div>
                      <label className={labelClass}>Description (Français)</label>
                      <textarea
                        value={form.descriptionFr}
                        onChange={(e) => setForm({ ...form, descriptionFr: e.target.value })}
                        placeholder="Description du livre..."
                        rows={4}
                        className={inputClass}
                      />
                    </div>
                  )}

                  {/* Image URL */}
                  <div>
                    <label className={labelClass}>{t('language') === 'ar' ? 'رابط الصورة' : 'Image URL'}</label>
                    <input
                      type="url"
                      value={form.image}
                      onChange={(e) => setForm({ ...form, image: e.target.value })}
                      placeholder="https://..."
                      className={inputClass}
                    />
                    {form.image && (
                      <img src={form.image} alt="Preview" className="mt-2 w-24 h-32 object-cover rounded-lg" />
                    )}
                  </div>
                </div>

                {/* Right Column */}
                <div className="space-y-4">
                  {/* Category */}
                  <div>
                    <label className={labelClass}>{t('category')} *</label>
                    <select
                      value={form.category}
                      onChange={(e) => setForm({ ...form, category: e.target.value as BookCategory })}
                      className={inputClass}
                    >
                      {categories.map((cat) => (
                        <option key={cat.key} value={cat.key}>{cat.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Price */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className={labelClass}>{t('price')} (USD) *</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={form.price}
                        onChange={(e) => setForm({ ...form, price: parseFloat(e.target.value) || 0 })}
                        required
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>{isRTL ? 'السعر الأصلي' : 'Original Price'}</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={form.originalPrice || ''}
                        onChange={(e) => setForm({ ...form, originalPrice: parseFloat(e.target.value) || undefined })}
                        placeholder="Optional"
                        className={inputClass}
                      />
                    </div>
                  </div>

                  {/* Book Details */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className={labelClass}>{t('pages')}</label>
                      <input
                        type="number"
                        min="1"
                        value={form.pages || ''}
                        onChange={(e) => setForm({ ...form, pages: parseInt(e.target.value) || undefined })}
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>{isRTL ? 'السنة' : 'Year'}</label>
                      <input
                        type="number"
                        min="1900"
                        max={new Date().getFullYear() + 1}
                        value={form.year}
                        onChange={(e) => setForm({ ...form, year: parseInt(e.target.value) || new Date().getFullYear() })}
                        className={inputClass}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className={labelClass}>{t('publisher')}</label>
                      <input
                        type="text"
                        value={form.publisher}
                        onChange={(e) => setForm({ ...form, publisher: e.target.value })}
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>{t('isbn')}</label>
                      <input
                        type="text"
                        value={form.isbn}
                        onChange={(e) => setForm({ ...form, isbn: e.target.value })}
                        placeholder="978-..."
                        className={inputClass}
                      />
                    </div>
                  </div>

                  <div>
                    <label className={labelClass}>{t('format')}</label>
                    <input
                      type="text"
                      value={form.format}
                      onChange={(e) => setForm({ ...form, format: e.target.value })}
                      placeholder="Paperback / PDF / MP3..."
                      className={inputClass}
                    />
                  </div>

                  {/* Rating */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className={labelClass}>{t('rating')} (1-5)</label>
                      <input
                        type="number"
                        step="0.1"
                        min="1"
                        max="5"
                        value={form.rating}
                        onChange={(e) => setForm({ ...form, rating: parseFloat(e.target.value) || 4.5 })}
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>{t('reviews')}</label>
                      <input
                        type="number"
                        min="0"
                        value={form.reviews}
                        onChange={(e) => setForm({ ...form, reviews: parseInt(e.target.value) || 0 })}
                        className={inputClass}
                      />
                    </div>
                  </div>

                  {/* Toggles */}
                  <div className={`p-4 rounded-xl space-y-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
                    {[
                      { key: 'inStock', label: t('inStock') },
                      { key: 'isNew', label: isRTL ? 'جديد' : 'New' },
                      { key: 'isBestSeller', label: isRTL ? 'الأكثر مبيعاً' : 'Best Seller' },
                      { key: 'isFeatured', label: isRTL ? 'مميز' : 'Featured' },
                    ].map((toggle) => (
                      <label key={toggle.key} className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={form[toggle.key as keyof typeof form] as boolean}
                          onChange={(e) => setForm({ ...form, [toggle.key]: e.target.checked })}
                          className="w-5 h-5 rounded border-gray-300 text-amber-500 focus:ring-amber-500"
                        />
                        <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{toggle.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              {/* Submit */}
              <div className="flex gap-3 mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                <button
                  type="button"
                  onClick={onClose}
                  className={`flex-1 py-3 rounded-xl font-semibold transition-colors ${
                    isDark ? 'bg-gray-800 text-gray-300 hover:bg-gray-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  className="flex-1 py-3 bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-colors"
                >
                  {editBook ? <Save className="w-5 h-5" /> : <Plus className="w-5 h-5" />}
                  {editBook ? t('save') : t('addProduct')}
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
