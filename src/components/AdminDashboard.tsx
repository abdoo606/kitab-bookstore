import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3, Package, Users, BookOpen, TrendingUp,
  Truck, CheckCircle2, Clock, Plus, Pencil, Trash2, AlertTriangle
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';
import BookFormModal from './BookFormModal';

type AdminTab = 'dashboard' | 'orders' | 'products' | 'users';

export default function AdminDashboard() {
  const { 
    isDark, orders, users, updateOrderStatus, language, 
    books, deleteBook, setEditingBook, editingBook,
    isAddBookModalOpen, setAddBookModalOpen
  } = useStore();
  const { t, formatPrice } = useTranslation();
  const [activeTab, setActiveTab] = useState<AdminTab>('dashboard');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const totalSales = orders.reduce((sum, o) => sum + o.total, 0);

  const statusColors: Record<string, string> = {
    pending: 'bg-yellow-500/20 text-yellow-500',
    processing: 'bg-blue-500/20 text-blue-500',
    shipped: 'bg-purple-500/20 text-purple-500',
    delivered: 'bg-emerald-500/20 text-emerald-500',
  };

  const statusIcons: Record<string, typeof Clock> = {
    pending: Clock,
    processing: Package,
    shipped: Truck,
    delivered: CheckCircle2,
  };

  const tabs: { key: AdminTab; label: string; icon: typeof BarChart3 }[] = [
    { key: 'dashboard', label: t('dashboard'), icon: BarChart3 },
    { key: 'orders', label: t('manageOrders'), icon: Package },
    { key: 'products', label: t('manageProducts'), icon: BookOpen },
    { key: 'users', label: t('manageUsers'), icon: Users },
  ];

  const handleDeleteBook = (id: string) => {
    deleteBook(id);
    setDeleteConfirm(null);
  };

  return (
    <div className={`min-h-screen pt-24 pb-16 ${isDark ? 'bg-gray-950' : 'bg-gray-50'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`text-3xl font-bold mb-8 ${isDark ? 'text-white' : 'text-gray-900'}`}
        >
          {t('admin')}
        </motion.h1>

        {/* Tabs */}
        <div className="flex flex-wrap gap-2 mb-8">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                activeTab === tab.key
                  ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/25'
                  : isDark ? 'bg-gray-800 text-gray-300 hover:bg-gray-700' : 'bg-white text-gray-600 hover:bg-gray-100 ring-1 ring-gray-200'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Dashboard */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: t('totalSales'), value: formatPrice(totalSales), icon: TrendingUp, color: 'text-emerald-500 bg-emerald-500/10' },
                { label: t('totalOrders'), value: orders.length.toString(), icon: Package, color: 'text-blue-500 bg-blue-500/10' },
                { label: t('totalUsers'), value: users.length.toString(), icon: Users, color: 'text-purple-500 bg-purple-500/10' },
                { label: t('totalProducts'), value: books.length.toString(), icon: BookOpen, color: 'text-amber-500 bg-amber-500/10' },
              ].map((stat, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className={`p-6 rounded-2xl ${isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200'}`}
                >
                  <div className={`w-12 h-12 flex items-center justify-center rounded-xl mb-3 ${stat.color}`}>
                    <stat.icon className="w-6 h-6" />
                  </div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{stat.value}</p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{stat.label}</p>
                </motion.div>
              ))}
            </div>

            {/* Recent Orders */}
            <div className={`p-6 rounded-2xl ${isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200'}`}>
              <h3 className={`text-lg font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {t('manageOrders')} ({orders.length})
              </h3>
              {orders.length === 0 ? (
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  {t('noResults')}
                </p>
              ) : (
                <div className="space-y-3">
                  {orders.slice(-5).reverse().map((order) => (
                    <div key={order.id} className={`flex items-center justify-between p-3 rounded-xl ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
                      <div>
                        <p className={`font-medium text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{order.id}</p>
                        <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                          {new Date(order.date).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`text-sm font-bold ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                          {formatPrice(order.total)}
                        </span>
                        <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${statusColors[order.status]}`}>
                          {t(order.status)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Orders Management */}
        {activeTab === 'orders' && (
          <div className={`p-6 rounded-2xl ${isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200'}`}>
            <h3 className={`text-lg font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {t('manageOrders')}
            </h3>
            {orders.length === 0 ? (
              <p className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('noResults')}</p>
            ) : (
              <div className="space-y-4">
                {[...orders].reverse().map((order) => (
                  <motion.div
                    key={order.id}
                    layout
                    className={`p-4 rounded-xl ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                      <div>
                        <p className={`font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{order.id}</p>
                        <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                          {order.shippingInfo.fullName} • {new Date(order.date).toLocaleDateString()}
                        </p>
                      </div>
                      <span className={`text-lg font-bold ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                        {formatPrice(order.total)}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(['pending', 'processing', 'shipped', 'delivered'] as const).map((s) => {
                        const SIcon = statusIcons[s];
                        return (
                          <button
                            key={s}
                            onClick={() => updateOrderStatus(order.id, s)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                              order.status === s
                                ? statusColors[s] + ' ring-2 ring-current'
                                : isDark ? 'bg-gray-700 text-gray-400 hover:bg-gray-600' : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
                            }`}
                          >
                            <SIcon className="w-3.5 h-3.5" />
                            {t(s)}
                          </button>
                        );
                      })}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Products Management */}
        {activeTab === 'products' && (
          <div className={`p-6 rounded-2xl ${isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200'}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className={`text-lg font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {t('manageProducts')} ({books.length})
              </h3>
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={() => setAddBookModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2.5 bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl text-sm transition-colors"
              >
                <Plus className="w-4 h-4" />
                {t('addProduct')}
              </motion.button>
            </div>
            
            <div className="space-y-3">
              {books.map((book) => {
                const title = language === 'ar' ? book.titleAr : language === 'fr' ? book.titleFr : book.title;
                return (
                  <motion.div 
                    key={book.id} 
                    layout
                    className={`flex items-center gap-4 p-3 rounded-xl ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}
                  >
                    <img src={book.image} alt={title} className="w-12 h-16 object-cover rounded-lg" />
                    <div className="flex-1 min-w-0">
                      <p className={`font-medium text-sm truncate ${isDark ? 'text-white' : 'text-gray-900'}`}>{title}</p>
                      <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t(book.category)}</p>
                    </div>
                    <span className={`font-bold text-sm ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                      {formatPrice(book.price)}
                    </span>
                    <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${
                      book.inStock ? 'bg-emerald-500/20 text-emerald-500' : 'bg-red-500/20 text-red-500'
                    }`}>
                      {book.inStock ? t('inStock') : t('outOfStock')}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setEditingBook(book)}
                        className={`p-2 rounded-lg transition-colors ${
                          isDark ? 'hover:bg-gray-700 text-blue-400' : 'hover:bg-blue-50 text-blue-600'
                        }`}
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(book.id)}
                        className={`p-2 rounded-lg transition-colors ${
                          isDark ? 'hover:bg-gray-700 text-red-400' : 'hover:bg-red-50 text-red-600'
                        }`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        )}

        {/* Users Management */}
        {activeTab === 'users' && (
          <div className={`p-6 rounded-2xl ${isDark ? 'bg-gray-900 ring-1 ring-gray-800' : 'bg-white ring-1 ring-gray-200'}`}>
            <h3 className={`text-lg font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {t('manageUsers')} ({users.length})
            </h3>
            <div className="space-y-3">
              {users.map((u) => (
                <div key={u.id} className={`flex items-center gap-4 p-3 rounded-xl ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
                  <div className={`w-10 h-10 flex items-center justify-center rounded-full ${
                    u.isAdmin ? 'bg-amber-500/20 text-amber-500' : isDark ? 'bg-gray-700 text-gray-400' : 'bg-gray-200 text-gray-500'
                  }`}>
                    <Users className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <p className={`font-medium text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{u.name}</p>
                    <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{u.email}</p>
                  </div>
                  <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${
                    u.isAdmin ? 'bg-amber-500/20 text-amber-500' : isDark ? 'bg-gray-700 text-gray-400' : 'bg-gray-200 text-gray-500'
                  }`}>
                    {u.isAdmin ? 'Admin' : 'User'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Add/Edit Book Modal */}
      <BookFormModal
        isOpen={isAddBookModalOpen || !!editingBook}
        onClose={() => { setAddBookModalOpen(false); setEditingBook(null); }}
        editBook={editingBook}
      />

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDeleteConfirm(null)}
              className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className={`fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm p-6 rounded-2xl ${
                isDark ? 'bg-gray-900' : 'bg-white'
              } shadow-2xl`}
            >
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 flex items-center justify-center rounded-full bg-red-500/20">
                  <AlertTriangle className="w-8 h-8 text-red-500" />
                </div>
                <h3 className={`text-xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {t('deleteProduct')}
                </h3>
                <p className={`text-sm mb-6 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  {language === 'ar' ? 'هل أنت متأكد من حذف هذا الكتاب؟' : 'Are you sure you want to delete this book?'}
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    className={`flex-1 py-2.5 rounded-xl font-semibold transition-colors ${
                      isDark ? 'bg-gray-800 text-gray-300 hover:bg-gray-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {t('cancel')}
                  </button>
                  <button
                    onClick={() => handleDeleteBook(deleteConfirm)}
                    className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-xl transition-colors"
                  >
                    {t('confirm')}
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
