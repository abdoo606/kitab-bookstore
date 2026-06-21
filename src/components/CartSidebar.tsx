import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, Minus, Trash2, ShoppingBag } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';

export default function CartSidebar() {
  const {
    isDark, cart, isCartOpen, setCartOpen,
    removeFromCart, updateQuantity, setPage, language,
  } = useStore();
  const { t, formatPrice, isRTL } = useTranslation();

  const subtotal = cart.reduce((sum, item) => sum + item.book.price * item.quantity, 0);

  return (
    <AnimatePresence>
      {isCartOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setCartOpen(false)}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          />

          {/* Sidebar */}
          <motion.div
            initial={{ x: isRTL ? -400 : 400 }}
            animate={{ x: 0 }}
            exit={{ x: isRTL ? -400 : 400 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className={`fixed top-0 ${isRTL ? 'left-0' : 'right-0'} z-50 h-full w-full max-w-md flex flex-col ${
              isDark ? 'bg-gray-900' : 'bg-white'
            } shadow-2xl`}
          >
            {/* Header */}
            <div className={`flex items-center justify-between p-6 border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {t('shoppingCart')} ({cart.length})
              </h2>
              <button
                onClick={() => setCartOpen(false)}
                className={`p-2 rounded-full transition-colors ${
                  isDark ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-500'
                }`}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Items */}
            <div className="flex-1 overflow-y-auto p-6">
              {cart.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full">
                  <ShoppingBag className={`w-20 h-20 mb-4 ${isDark ? 'text-gray-700' : 'text-gray-200'}`} />
                  <p className={`text-lg font-medium mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    {t('cartEmpty')}
                  </p>
                  <button
                    onClick={() => { setCartOpen(false); setPage('books'); }}
                    className="mt-4 px-6 py-2.5 bg-amber-500 text-white rounded-xl font-medium"
                  >
                    {t('continueShopping')}
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {cart.map((item) => {
                    const title = language === 'ar' ? item.book.titleAr : language === 'fr' ? item.book.titleFr : item.book.title;
                    return (
                      <motion.div
                        key={item.book.id}
                        layout
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, x: isRTL ? -100 : 100 }}
                        className={`flex gap-4 p-3 rounded-xl ${
                          isDark ? 'bg-gray-800' : 'bg-gray-50'
                        }`}
                      >
                        <img
                          src={item.book.image}
                          alt={title}
                          className="w-20 h-28 object-cover rounded-lg"
                        />
                        <div className="flex-1 min-w-0">
                          <h3 className={`font-medium text-sm line-clamp-2 mb-1 ${
                            isDark ? 'text-white' : 'text-gray-900'
                          }`}>
                            {title}
                          </h3>
                          <p className={`text-sm font-bold ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                            {formatPrice(item.book.price)}
                          </p>
                          <div className="flex items-center justify-between mt-2">
                            <div className={`flex items-center gap-1 rounded-lg ${
                              isDark ? 'bg-gray-700' : 'bg-white ring-1 ring-gray-200'
                            }`}>
                              <button
                                onClick={() => updateQuantity(item.book.id, item.quantity - 1)}
                                className={`p-1.5 rounded-lg transition-colors ${
                                  isDark ? 'hover:bg-gray-600' : 'hover:bg-gray-100'
                                }`}
                              >
                                <Minus className="w-3.5 h-3.5" />
                              </button>
                              <span className={`w-8 text-center text-sm font-medium ${
                                isDark ? 'text-white' : 'text-gray-900'
                              }`}>
                                {item.quantity}
                              </span>
                              <button
                                onClick={() => updateQuantity(item.book.id, item.quantity + 1)}
                                className={`p-1.5 rounded-lg transition-colors ${
                                  isDark ? 'hover:bg-gray-600' : 'hover:bg-gray-100'
                                }`}
                              >
                                <Plus className="w-3.5 h-3.5" />
                              </button>
                            </div>
                            <button
                              onClick={() => removeFromCart(item.book.id)}
                              className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer */}
            {cart.length > 0 && (
              <div className={`p-6 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between">
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('subtotal')}</span>
                    <span className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {formatPrice(subtotal)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('shipping')}</span>
                    <span className="text-emerald-500 font-medium">{t('freeShipping')}</span>
                  </div>
                  <div className={`flex justify-between pt-2 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                    <span className={`font-bold text-lg ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('total')}</span>
                    <span className={`font-bold text-lg ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                      {formatPrice(subtotal)}
                    </span>
                  </div>
                </div>
                <motion.button
                  whileTap={{ scale: 0.98 }}
                  onClick={() => { setCartOpen(false); setPage('checkout'); }}
                  className="w-full py-3.5 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl transition-colors"
                >
                  {t('checkout')}
                </motion.button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
