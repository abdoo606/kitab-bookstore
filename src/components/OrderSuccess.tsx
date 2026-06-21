import { motion } from 'framer-motion';
import { CheckCircle2, ArrowRight, ArrowLeft } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';

export default function OrderSuccess() {
  const { isDark, setPage } = useStore();
  const { t, isRTL } = useTranslation();

  const Arrow = isRTL ? ArrowLeft : ArrowRight;

  return (
    <div className={`min-h-screen flex items-center justify-center px-4 ${isDark ? 'bg-gray-950' : 'bg-gray-50'}`}>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center max-w-md"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', delay: 0.2, stiffness: 200 }}
          className="w-24 h-24 mx-auto mb-6 flex items-center justify-center rounded-full bg-emerald-500/20"
        >
          <CheckCircle2 className="w-12 h-12 text-emerald-500" />
        </motion.div>

        <h1 className={`text-3xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          {t('orderPlaced')}
        </h1>

        <p className={`text-lg mb-8 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          {t('orderConfirmation')}
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={() => setPage('orders')}
            className="flex items-center justify-center gap-2 px-6 py-3 bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl transition-colors"
          >
            {t('orders')}
            <Arrow className="w-4 h-4" />
          </motion.button>
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={() => setPage('home')}
            className={`px-6 py-3 font-semibold rounded-xl border-2 transition-colors ${
              isDark ? 'border-gray-700 text-gray-300 hover:bg-gray-800' : 'border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {t('continueShopping')}
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}
