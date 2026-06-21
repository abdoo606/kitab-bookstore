import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, ArrowLeft } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';

export default function PromoBanner() {
  const { isDark, setPage, setCategory } = useStore();
  const { t, isRTL } = useTranslation();

  const Arrow = isRTL ? ArrowLeft : ArrowRight;

  return (
    <section className={`py-20 ${isDark ? 'bg-gray-950' : 'bg-white'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="grid md:grid-cols-2 gap-6">
          {/* E-Books Promo */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="relative overflow-hidden rounded-2xl h-72"
          >
            <img
              src="https://images.pexels.com/photos/844734/pexels-photo-844734.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=600&w=800"
              alt="E-books"
              className="absolute inset-0 w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-blue-900/90 to-blue-900/50" />
            <div className="relative z-10 p-8 flex flex-col justify-center h-full">
              <span className="inline-flex items-center gap-1 text-blue-300 text-sm font-medium mb-2">
                <Sparkles className="w-4 h-4" />
                {isRTL ? 'عروض حصرية' : 'Exclusive Deals'}
              </span>
              <h3 className="text-white text-2xl sm:text-3xl font-bold mb-2">
                {isRTL ? 'كتب إلكترونية' : 'E-Books'}
              </h3>
              <p className="text-blue-200 text-sm mb-4">
                {isRTL ? 'خصم 30% على جميع الكتب الإلكترونية' : '30% off all e-books this week'}
              </p>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => { setCategory('ebook'); setPage('books'); }}
                className="self-start flex items-center gap-2 px-6 py-2.5 bg-white text-blue-900 font-semibold rounded-xl text-sm"
              >
                {t('shopNow')}
                <Arrow className="w-4 h-4" />
              </motion.button>
            </div>
          </motion.div>

          {/* Audiobooks Promo */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="relative overflow-hidden rounded-2xl h-72"
          >
            <img
              src="https://images.pexels.com/photos/3394659/pexels-photo-3394659.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=600&w=800"
              alt="Audiobooks"
              className="absolute inset-0 w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-purple-900/90 to-purple-900/50" />
            <div className="relative z-10 p-8 flex flex-col justify-center h-full">
              <span className="inline-flex items-center gap-1 text-purple-300 text-sm font-medium mb-2">
                <Sparkles className="w-4 h-4" />
                {isRTL ? 'وصل حديثاً' : 'New Arrivals'}
              </span>
              <h3 className="text-white text-2xl sm:text-3xl font-bold mb-2">
                {isRTL ? 'كتب صوتية' : 'Audiobooks'}
              </h3>
              <p className="text-purple-200 text-sm mb-4">
                {isRTL ? 'استمع أثناء التنقل — مجموعة جديدة' : 'Listen on the go — new collection'}
              </p>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => { setCategory('audiobook'); setPage('books'); }}
                className="self-start flex items-center gap-2 px-6 py-2.5 bg-white text-purple-900 font-semibold rounded-xl text-sm"
              >
                {t('shopNow')}
                <Arrow className="w-4 h-4" />
              </motion.button>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
