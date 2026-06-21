import { motion } from 'framer-motion';
import { Package, Clock, Truck, CheckCircle2, ShoppingBag } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';

export default function OrdersPage() {
  const { isDark, orders, user, language } = useStore();
  const { t, formatPrice } = useTranslation();

  const userOrders = orders.filter((o) => o.userId === user?.id).reverse();

  const statusSteps = ['pending', 'processing', 'shipped', 'delivered'];
  const statusIcons = [Clock, Package, Truck, CheckCircle2];

  return (
    <div className={`min-h-screen pt-24 pb-16 ${isDark ? 'bg-gray-950' : 'bg-gray-50'}`}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`text-3xl font-bold mb-8 ${isDark ? 'text-white' : 'text-gray-900'}`}
        >
          {t('orders')}
        </motion.h1>

        {userOrders.length === 0 ? (
          <div className="text-center py-20">
            <ShoppingBag className={`w-20 h-20 mx-auto mb-4 ${isDark ? 'text-gray-700' : 'text-gray-200'}`} />
            <p className={`text-xl font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              {t('noResults')}
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {userOrders.map((order, idx) => {
              const currentStep = statusSteps.indexOf(order.status);
              return (
                <motion.div
                  key={order.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`p-6 rounded-2xl ${isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200'}`}
                >
                  {/* Header */}
                  <div className="flex flex-wrap justify-between gap-3 mb-6">
                    <div>
                      <p className={`font-bold text-lg ${isDark ? 'text-white' : 'text-gray-900'}`}>{order.id}</p>
                      <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {new Date(order.date).toLocaleDateString()} • {order.items.length} {t('books')}
                      </p>
                    </div>
                    <p className={`text-2xl font-bold ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                      {formatPrice(order.total)}
                    </p>
                  </div>

                  {/* Progress Bar */}
                  <div className="flex items-center justify-between mb-6">
                    {statusSteps.map((step, i) => {
                      const Icon = statusIcons[i];
                      const isActive = i <= currentStep;
                      return (
                        <div key={step} className="flex items-center flex-1">
                          <div className="flex flex-col items-center">
                            <div className={`w-10 h-10 flex items-center justify-center rounded-full transition-colors ${
                              isActive ? 'bg-amber-500 text-white' : isDark ? 'bg-gray-800 text-gray-500' : 'bg-gray-200 text-gray-400'
                            }`}>
                              <Icon className="w-5 h-5" />
                            </div>
                            <span className={`text-xs mt-1 font-medium hidden sm:block ${
                              isActive ? isDark ? 'text-amber-400' : 'text-amber-600' : isDark ? 'text-gray-500' : 'text-gray-400'
                            }`}>
                              {t(step)}
                            </span>
                          </div>
                          {i < statusSteps.length - 1 && (
                            <div className={`flex-1 h-1 mx-2 rounded-full ${
                              i < currentStep ? 'bg-amber-500' : isDark ? 'bg-gray-800' : 'bg-gray-200'
                            }`} />
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Items */}
                  <div className="space-y-2">
                    {order.items.map((item) => {
                      const title = language === 'ar' ? item.book.titleAr : item.book.title;
                      return (
                        <div key={item.book.id} className={`flex items-center gap-3 p-2 rounded-xl ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
                          <img src={item.book.image} alt={title} className="w-10 h-14 object-cover rounded-lg" />
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-medium truncate ${isDark ? 'text-white' : 'text-gray-900'}`}>{title}</p>
                            <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>x{item.quantity}</p>
                          </div>
                          <p className={`text-sm font-semibold ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                            {formatPrice(item.book.price * item.quantity)}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
