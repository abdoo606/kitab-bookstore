import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useStore } from './store/useStore';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Categories from './components/Categories';
import FeaturedBooks from './components/FeaturedBooks';
import PromoBanner from './components/PromoBanner';
import BooksPage from './components/BooksPage';
import NewArrivalsPage from './components/NewArrivalsPage';
import OffersPage from './components/OffersPage';
import CartSidebar from './components/CartSidebar';
import BookModal from './components/BookModal';
import CheckoutPage from './components/CheckoutPage';
import AuthPage from './components/AuthPage';
import AdminDashboard from './components/AdminDashboard';
import OrdersPage from './components/OrdersPage';
import OrderSuccess from './components/OrderSuccess';
import Footer from './components/Footer';

function App() {
  const { isDark, currentPage, language } = useStore();

  // Apply dark mode and RTL
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [isDark, language]);

  // Scroll to top on page change
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentPage]);

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return (
          <motion.div
            key="home"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Hero />
            <Categories />
            <FeaturedBooks />
            <PromoBanner />
            <Footer />
          </motion.div>
        );
      case 'books':
        return (
          <motion.div
            key="books"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <BooksPage />
            <Footer />
          </motion.div>
        );
      case 'newArrivals':
        return (
          <motion.div
            key="newArrivals"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <NewArrivalsPage />
            <Footer />
          </motion.div>
        );
      case 'offers':
        return (
          <motion.div
            key="offers"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <OffersPage />
            <Footer />
          </motion.div>
        );
      case 'checkout':
        return (
          <motion.div
            key="checkout"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <CheckoutPage />
          </motion.div>
        );
      case 'login':
        return (
          <motion.div
            key="login"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <AuthPage mode="login" />
          </motion.div>
        );
      case 'register':
        return (
          <motion.div
            key="register"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <AuthPage mode="register" />
          </motion.div>
        );
      case 'admin':
        return (
          <motion.div
            key="admin"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <AdminDashboard />
          </motion.div>
        );
      case 'orders':
        return (
          <motion.div
            key="orders"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <OrdersPage />
          </motion.div>
        );
      case 'orderSuccess':
        return (
          <motion.div
            key="success"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <OrderSuccess />
          </motion.div>
        );
      default:
        return null;
    }
  };

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      isDark ? 'bg-gray-950 text-white' : 'bg-white text-gray-900'
    }`} style={{ fontFamily: language === 'ar' ? '"Tajawal", "Cairo", sans-serif' : '"Inter", sans-serif' }}>
      <Navbar />
      <AnimatePresence mode="wait">
        {renderPage()}
      </AnimatePresence>
      <CartSidebar />
      <BookModal />
    </div>
  );
}

export default App;
