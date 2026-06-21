import { BookOpen, Mail, Phone, MapPin, Globe, MessageCircle, Camera, Play } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTranslation } from '../hooks/useTranslation';

export default function Footer() {
  const { isDark, setPage } = useStore();
  const { t, isRTL } = useTranslation();

  return (
    <footer className={`${isDark ? 'bg-gray-900 border-gray-800' : 'bg-gray-100 border-gray-200'} border-t`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className={`w-7 h-7 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
              <span className={`text-xl font-bold tracking-wider ${isDark ? 'text-white' : 'text-gray-900'}`}>KITAB</span>
            </div>
            <p className={`text-sm leading-relaxed mb-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              {t('aboutText')}
            </p>
            <div className="flex gap-3">
              {[Globe, MessageCircle, Camera, Play].map((Icon, i) => (
                <a
                  key={i}
                  href="#"
                  className={`w-9 h-9 flex items-center justify-center rounded-lg transition-colors ${
                    isDark ? 'bg-gray-800 text-gray-400 hover:text-amber-400 hover:bg-gray-700' : 'bg-gray-200 text-gray-500 hover:text-amber-600 hover:bg-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('quickLinks')}</h3>
            <ul className="space-y-2">
              {[
                { label: t('home'), page: 'home' as const },
                { label: t('books'), page: 'books' as const },
                { label: t('cart'), page: 'cart' as const },
                { label: t('login'), page: 'login' as const },
              ].map((link) => (
                <li key={link.page}>
                  <button
                    onClick={() => setPage(link.page)}
                    className={`text-sm transition-colors ${
                      isDark ? 'text-gray-400 hover:text-amber-400' : 'text-gray-500 hover:text-amber-600'
                    }`}
                  >
                    {link.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h3 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('contactUs')}</h3>
            <ul className="space-y-3">
              {[
                { icon: Mail, text: 'info@kitab-store.com' },
                { icon: Phone, text: '+1 (555) 123-4567' },
                { icon: MapPin, text: isRTL ? 'دبي، الإمارات العربية المتحدة' : 'Dubai, UAE' },
              ].map((item, i) => (
                <li key={i} className="flex items-center gap-2">
                  <item.icon className={`w-4 h-4 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
                  <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{item.text}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Newsletter */}
          <div>
            <h3 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('newsletter')}</h3>
            <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              {t('newsletterText')}
            </p>
            <div className="flex gap-2">
              <input
                type="email"
                placeholder={t('enterEmail')}
                dir={isRTL ? 'rtl' : 'ltr'}
                className={`flex-1 px-4 py-2.5 rounded-xl text-sm border outline-none transition-colors ${
                  isDark
                    ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-500 focus:border-amber-500'
                    : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-amber-500'
                }`}
              />
              <button className="px-4 py-2.5 bg-amber-500 hover:bg-amber-600 text-white font-medium rounded-xl text-sm transition-colors">
                {t('subscribe')}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className={`border-t ${isDark ? 'border-gray-800' : 'border-gray-200'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 text-center">
          <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            © {new Date().getFullYear()} KITAB. {t('allRightsReserved')}.
          </p>
        </div>
      </div>
    </footer>
  );
}
