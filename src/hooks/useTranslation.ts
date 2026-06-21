import { useStore } from '../store/useStore';
import { translations, currencyRates, currencySymbols } from '../i18n/translations';

export function useTranslation() {
  const language = useStore((s) => s.language);
  const currency = useStore((s) => s.currency);

  const t = (key: string): string => {
    return translations[language]?.[key] || translations['en']?.[key] || key;
  };

  const formatPrice = (priceUSD: number): string => {
    const converted = priceUSD * currencyRates[currency];
    const symbol = currencySymbols[currency];
    if (language === 'ar') {
      return `${converted.toFixed(2)} ${symbol}`;
    }
    return `${symbol}${converted.toFixed(2)}`;
  };

  const isRTL = language === 'ar';

  return { t, formatPrice, language, currency, isRTL };
}
