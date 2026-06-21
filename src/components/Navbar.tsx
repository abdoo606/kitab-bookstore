import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BookOpen, ShoppingCart, Sun, Moon, Menu, X, Search,
  User, LogOut, Shield, Globe, ChevronDown, Package
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';
import type { Language, Currency } from '../i18n/translations';

export default function Navbar() {
  const {
    isDark, toggleTheme, cart, user, logoutUser,
    setPage, currentPage, searchQuery, setSearchQuery,
    isMobileMenuOpen, setMobileMenuOpen, setCartOpen,
    language, setLanguage, currency, setCurrency,
  } = useStore();
  const { t, isRTL } = useTranslation();
  const [showLangMenu, setShowLangMenu] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);

  const languages: { code: Language; label: string; flag: string }[] = [
    { code: 'ar', label: 'العربية', flag: '🇸🇦' },
    { code: 'en', label: 'English', flag: '🇺🇸' },
    { code: 'fr', label: 'Français', flag: '🇫🇷' },
  ];

  const currencies: Currency[] = ['USD', 'SAR', 'EUR'];

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-300 ${
      isDark ? 'bg-gray-900/95 border-gray-700' : 'bg-white/95 border-gray-200'
    } backdrop-blur-md border-b`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setPage('home')}
            className="flex items-center gap-2"
          >
            <BookOpen className={`w-8 h-8 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
            <span className={`text-2xl font-bold tracking-wider ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>
              KITAB
            </span>
          </motion.button>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-1">
            {([
              { key: 'home', label: t('home') },
              { key: 'books', label: t('books') },
              { key: 'newArrivals', label: t('newArrivalsPage') },
              { key: 'offers', label: t('offersPage') },
            ] as const).map((item) => (
              <button
                key={item.key}
                onClick={() => setPage(item.key)}
                className={`relative px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  currentPage === item.key
                    ? isDark ? 'text-amber-400 bg-amber-500/10' : 'text-amber-600 bg-amber-50'
                    : isDark ? 'text-gray-300 hover:text-white hover:bg-gray-800' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                {item.label}
                {item.key === 'newArrivals' && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                )}
                {item.key === 'offers' && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                )}
              </button>
            ))}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Search Toggle */}
            <button
              onClick={() => setShowSearch(!showSearch)}
              className={`p-2 rounded-full transition-colors ${
                isDark ? 'hover:bg-gray-800 text-gray-300' : 'hover:bg-gray-100 text-gray-600'
              }`}
            >
              <Search className="w-5 h-5" />
            </button>

            {/* Language & Currency */}
            <div className="relative hidden sm:block">
              <button
                onClick={() => setShowLangMenu(!showLangMenu)}
                className={`flex items-center gap-1 p-2 rounded-full transition-colors ${
                  isDark ? 'hover:bg-gray-800 text-gray-300' : 'hover:bg-gray-100 text-gray-600'
                }`}
              >
                <Globe className="w-5 h-5" />
                <ChevronDown className="w-3 h-3" />
              </button>
              <AnimatePresence>
                {showLangMenu && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className={`absolute ${isRTL ? 'left-0' : 'right-0'} top-12 w-48 rounded-xl shadow-xl border overflow-hidden ${
                      isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
                    }`}
                  >
                    <div className="p-2">
                      <p className={`text-xs font-semibold px-3 py-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {t('language')}
                      </p>
                      {languages.map((lang) => (
                        <button
                          key={lang.code}
                          onClick={() => { setLanguage(lang.code); setShowLangMenu(false); }}
                          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                            language === lang.code
                              ? isDark ? 'bg-amber-500/20 text-amber-400' : 'bg-amber-50 text-amber-600'
                              : isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          <span>{lang.flag}</span>
                          <span>{lang.label}</span>
                        </button>
                      ))}
                      <div className={`my-2 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`} />
                      <p className={`text-xs font-semibold px-3 py-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {t('price')}
                      </p>
                      {currencies.map((curr) => (
                        <button
                          key={curr}
                          onClick={() => { setCurrency(curr); setShowLangMenu(false); }}
                          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                            currency === curr
                              ? isDark ? 'bg-amber-500/20 text-amber-400' : 'bg-amber-50 text-amber-600'
                              : isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          {curr}
                        </button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className={`p-2 rounded-full transition-colors ${
                isDark ? 'hover:bg-gray-800 text-amber-400' : 'hover:bg-gray-100 text-gray-600'
              }`}
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>

            {/* Cart */}
            <button
              onClick={() => setCartOpen(true)}
              className={`relative p-2 rounded-full transition-colors ${
                isDark ? 'hover:bg-gray-800 text-gray-300' : 'hover:bg-gray-100 text-gray-600'
              }`}
            >
              <ShoppingCart className="w-5 h-5" />
              {cartCount > 0 && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center text-xs font-bold text-white bg-amber-500 rounded-full"
                >
                  {cartCount}
                </motion.span>
              )}
            </button>

            {/* User */}
            {user ? (
              <div className="hidden sm:flex items-center gap-2">
                {user.isAdmin && (
                  <button
                    onClick={() => setPage('admin')}
                    className={`p-2 rounded-full transition-colors ${
                      isDark ? 'hover:bg-gray-800 text-amber-400' : 'hover:bg-gray-100 text-amber-600'
                    }`}
                  >
                    <Shield className="w-5 h-5" />
                  </button>
                )}
                <button
                  onClick={() => setPage('orders')}
                  className={`p-2 rounded-full transition-colors ${
                    isDark ? 'hover:bg-gray-800 text-gray-300' : 'hover:bg-gray-100 text-gray-600'
                  }`}
                >
                  <Package className="w-5 h-5" />
                </button>
                <button
                  onClick={logoutUser}
                  className={`p-2 rounded-full transition-colors ${
                    isDark ? 'hover:bg-gray-800 text-gray-300' : 'hover:bg-gray-100 text-gray-600'
                  }`}
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setPage('login')}
                className={`hidden sm:block p-2 rounded-full transition-colors ${
                  isDark ? 'hover:bg-gray-800 text-gray-300' : 'hover:bg-gray-100 text-gray-600'
                }`}
              >
                <User className="w-5 h-5" />
              </button>
            )}

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!isMobileMenuOpen)}
              className={`md:hidden p-2 rounded-full transition-colors ${
                isDark ? 'hover:bg-gray-800 text-gray-300' : 'hover:bg-gray-100 text-gray-600'
              }`}
            >
              {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <AnimatePresence>
          {showSearch && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="pb-4">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    if (currentPage !== 'books') setPage('books');
                  }}
                  placeholder={t('search')}
                  className={`w-full px-4 py-2.5 rounded-xl border outline-none transition-colors ${
                    isDark
                      ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500 focus:border-amber-500'
                      : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400 focus:border-amber-500'
                  }`}
                  dir={isRTL ? 'rtl' : 'ltr'}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className={`md:hidden overflow-hidden border-t ${
              isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'
            }`}
          >
            <div className="px-4 py-4 space-y-2">
              {([
                { key: 'home' as const, label: t('home'), dot: '' },
                { key: 'books' as const, label: t('books'), dot: '' },
                { key: 'newArrivals' as const, label: t('newArrivalsPage'), dot: 'bg-emerald-500' },
                { key: 'offers' as const, label: t('offersPage'), dot: 'bg-red-500' },
              ]).map((item) => (
                <button
                  key={item.key}
                  onClick={() => setPage(item.key)}
                  className={`relative block w-full text-start px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    currentPage === item.key
                      ? isDark ? 'bg-amber-500/20 text-amber-400' : 'bg-amber-50 text-amber-600'
                      : isDark ? 'text-gray-300 hover:bg-gray-800' : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {item.label}
                    {item.dot && <span className={`w-2 h-2 rounded-full animate-pulse ${item.dot}`} />}
                  </span>
                </button>
              ))}
              
              {/* Mobile language & currency */}
              <div className={`pt-2 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                <div className="flex gap-2 flex-wrap">
                  {languages.map((lang) => (
                    <button
                      key={lang.code}
                      onClick={() => setLanguage(lang.code)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        language === lang.code
                          ? 'bg-amber-500 text-white'
                          : isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {lang.flag} {lang.label}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2 mt-2">
                  {currencies.map((curr) => (
                    <button
                      key={curr}
                      onClick={() => setCurrency(curr)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        currency === curr
                          ? 'bg-amber-500 text-white'
                          : isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {curr}
                    </button>
                  ))}
                </div>
              </div>

              {user ? (
                <div className={`pt-2 border-t space-y-2 ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                  {user.isAdmin && (
                    <button onClick={() => setPage('admin')} className={`block w-full text-start px-4 py-2.5 rounded-lg text-sm font-medium ${isDark ? 'text-amber-400 hover:bg-gray-800' : 'text-amber-600 hover:bg-gray-50'}`}>
                      {t('admin')}
                    </button>
                  )}
                  <button onClick={() => setPage('orders')} className={`block w-full text-start px-4 py-2.5 rounded-lg text-sm font-medium ${isDark ? 'text-gray-300 hover:bg-gray-800' : 'text-gray-600 hover:bg-gray-50'}`}>
                    {t('orders')}
                  </button>
                  <button onClick={logoutUser} className="block w-full text-start px-4 py-2.5 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20">
                    {t('logout')}
                  </button>
                </div>
              ) : (
                <div className={`pt-2 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                  <button onClick={() => setPage('login')} className={`block w-full text-start px-4 py-2.5 rounded-lg text-sm font-medium ${isDark ? 'text-gray-300 hover:bg-gray-800' : 'text-gray-600 hover:bg-gray-50'}`}>
                    {t('login')}
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
