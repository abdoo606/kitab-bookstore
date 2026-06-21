import { useState } from 'react';
import { motion } from 'framer-motion';
import { CreditCard, Truck, Smartphone, Building2, Lock } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';

export default function CheckoutPage() {
  const { isDark, cart, clearCart, addOrder, setPage, user, currency } = useStore();
  const { t, formatPrice, isRTL } = useTranslation();

  const [paymentMethod, setPaymentMethod] = useState('creditCard');
  const [form, setForm] = useState({
    fullName: user?.name || '',
    email: user?.email || '',
    phone: '',
    address: '',
    city: '',
    country: '',
    cardNumber: '',
    expiryDate: '',
    cvv: '',
  });

  const subtotal = cart.reduce((sum, item) => sum + item.book.price * item.quantity, 0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addOrder({
      userId: user?.id || 'guest',
      items: cart,
      total: subtotal,
      currency,
      shippingInfo: {
        fullName: form.fullName,
        email: form.email,
        phone: form.phone,
        address: form.address,
        city: form.city,
        country: form.country,
      },
      paymentMethod,
    });
    clearCart();
    setPage('orderSuccess');
  };

  const payments = [
    { key: 'creditCard', label: t('creditCard'), icon: CreditCard },
    { key: 'cashOnDelivery', label: t('cashOnDelivery'), icon: Truck },
    { key: 'applePay', label: t('applePay'), icon: Smartphone },
    { key: 'bankTransfer', label: t('bankTransfer'), icon: Building2 },
  ];

  const inputClass = `w-full px-4 py-3 rounded-xl border outline-none transition-colors ${
    isDark
      ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500 focus:border-amber-500'
      : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-amber-500'
  }`;

  return (
    <div className={`min-h-screen pt-24 pb-16 ${isDark ? 'bg-gray-950' : 'bg-gray-50'}`}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`text-3xl font-bold mb-8 ${isDark ? 'text-white' : 'text-gray-900'}`}
        >
          {t('checkoutTitle')}
        </motion.h1>

        <form onSubmit={handleSubmit} className="grid lg:grid-cols-3 gap-8">
          {/* Left - Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Shipping Info */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className={`p-6 rounded-2xl ${isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200'}`}
            >
              <h2 className={`text-lg font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {t('shippingInfo')}
              </h2>
              <div className="grid sm:grid-cols-2 gap-4" dir={isRTL ? 'rtl' : 'ltr'}>
                <input required type="text" placeholder={t('fullName')} value={form.fullName}
                  onChange={(e) => setForm({ ...form, fullName: e.target.value })} className={inputClass} />
                <input required type="email" placeholder={t('email')} value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })} className={inputClass} />
                <input required type="tel" placeholder={t('phone')} value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })} className={inputClass} />
                <input required type="text" placeholder={t('city')} value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })} className={inputClass} />
                <input required type="text" placeholder={t('address')} value={form.address}
                  onChange={(e) => setForm({ ...form, address: e.target.value })} className={`${inputClass} sm:col-span-2`} />
                <input required type="text" placeholder={t('country')} value={form.country}
                  onChange={(e) => setForm({ ...form, country: e.target.value })} className={inputClass} />
              </div>
            </motion.div>

            {/* Payment */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className={`p-6 rounded-2xl ${isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200'}`}
            >
              <h2 className={`text-lg font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {t('paymentMethod')}
              </h2>
              <div className="grid sm:grid-cols-2 gap-3 mb-4">
                {payments.map((pm) => (
                  <button
                    key={pm.key}
                    type="button"
                    onClick={() => setPaymentMethod(pm.key)}
                    className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                      paymentMethod === pm.key
                        ? 'border-amber-500 bg-amber-500/10'
                        : isDark ? 'border-gray-700 hover:border-gray-600' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <pm.icon className={`w-5 h-5 ${
                      paymentMethod === pm.key
                        ? 'text-amber-500'
                        : isDark ? 'text-gray-400' : 'text-gray-500'
                    }`} />
                    <span className={`text-sm font-medium ${
                      paymentMethod === pm.key
                        ? isDark ? 'text-amber-400' : 'text-amber-600'
                        : isDark ? 'text-gray-300' : 'text-gray-700'
                    }`}>
                      {pm.label}
                    </span>
                  </button>
                ))}
              </div>

              {paymentMethod === 'creditCard' && (
                <div className="grid sm:grid-cols-3 gap-4" dir="ltr">
                  <input type="text" placeholder={t('cardNumber')} value={form.cardNumber}
                    onChange={(e) => setForm({ ...form, cardNumber: e.target.value })} className={`${inputClass} sm:col-span-3`} />
                  <input type="text" placeholder={t('expiryDate')} value={form.expiryDate}
                    onChange={(e) => setForm({ ...form, expiryDate: e.target.value })} className={inputClass} />
                  <input type="text" placeholder={t('cvv')} value={form.cvv}
                    onChange={(e) => setForm({ ...form, cvv: e.target.value })} className={inputClass} />
                </div>
              )}
            </motion.div>
          </div>

          {/* Right - Summary */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className={`h-fit p-6 rounded-2xl sticky top-24 ${
              isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200'
            }`}
          >
            <h2 className={`text-lg font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {t('shoppingCart')}
            </h2>

            <div className="space-y-3 mb-4">
              {cart.map((item) => {
                const title = useStore.getState().language === 'ar' ? item.book.titleAr : item.book.title;
                return (
                  <div key={item.book.id} className="flex items-center gap-3">
                    <img src={item.book.image} alt={title} className="w-12 h-16 object-cover rounded-lg" />
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

            <div className={`space-y-2 pt-4 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <div className="flex justify-between">
                <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('subtotal')}</span>
                <span className={isDark ? 'text-white' : 'text-gray-900'}>{formatPrice(subtotal)}</span>
              </div>
              <div className="flex justify-between">
                <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('shipping')}</span>
                <span className="text-emerald-500">{t('freeShipping')}</span>
              </div>
              <div className={`flex justify-between pt-2 border-t font-bold text-lg ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                <span className={isDark ? 'text-white' : 'text-gray-900'}>{t('total')}</span>
                <span className={isDark ? 'text-amber-400' : 'text-amber-600'}>{formatPrice(subtotal)}</span>
              </div>
            </div>

            <motion.button
              whileTap={{ scale: 0.98 }}
              type="submit"
              className="w-full mt-6 py-3.5 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-colors"
            >
              <Lock className="w-4 h-4" />
              {t('placeOrder')}
            </motion.button>
          </motion.div>
        </form>
      </div>
    </div>
  );
}
