# 🎨 KITAB Customization Guide / دليل التخصيص / Guide de Personnalisation

---

## 🇺🇸 English

### 🏷️ Change Store Name & Branding

#### 1. Store Name
Edit `src/components/Navbar.tsx` line 47:
```tsx
<span>KITAB</span>  // Change to your store name
```

Edit `src/components/Footer.tsx` line 11:
```tsx
<span>KITAB</span>  // Change to your store name
```

#### 2. Page Title
Edit `index.html`:
```html
<title>YOUR STORE NAME — Premium Bookstore</title>
```

#### 3. About Text
Edit `src/i18n/translations.ts`:
```typescript
aboutText: 'Your custom about text here...',
```

### 🎨 Change Colors

The main accent color is **amber-500**. To change:

1. Search for `amber-500`, `amber-400`, `amber-600` in all files
2. Replace with your preferred color (e.g., `blue-500`, `emerald-500`, `rose-500`)

Common Tailwind colors:
- `blue-500` - Blue
- `emerald-500` - Green
- `rose-500` - Pink
- `purple-500` - Purple
- `indigo-500` - Indigo
- `cyan-500` - Cyan

### 📷 Change Images

#### Hero Image
Edit `src/components/Hero.tsx` line 16:
```tsx
src="YOUR_IMAGE_URL"
```

#### Category Images
Edit `src/data/books.ts` - `categoryImages` object at the bottom.

#### Book Images
Add new books via Admin Panel or edit `src/data/books.ts`.

### 💰 Change Currency

#### Add New Currency
Edit `src/i18n/translations.ts`:
```typescript
export const currencyRates: Record<Currency, number> = {
  USD: 1,
  SAR: 3.75,
  EUR: 0.92,
  GBP: 0.79,  // Add new
};

export const currencySymbols: Record<Currency, string> = {
  USD: '$',
  SAR: 'ر.س',
  EUR: '€',
  GBP: '£',  // Add new
};
```

Update the Currency type:
```typescript
export type Currency = 'USD' | 'SAR' | 'EUR' | 'GBP';
```

### 🌍 Add New Language

1. Edit `src/i18n/translations.ts`:
```typescript
export type Language = 'ar' | 'en' | 'fr' | 'es';  // Add 'es' for Spanish

// Add translations
es: {
  home: 'Inicio',
  books: 'Libros',
  // ... all other translations
}
```

2. Update Navbar language selector in `src/components/Navbar.tsx`.

### 📱 Change Admin Credentials

Edit `src/store/useStore.ts`:
```typescript
// Line 105
const passwords: Record<string, string> = {
  'your-admin@email.com': 'your-password',
};

// Line 176
users: [
  { id: '1', name: 'Admin', email: 'your-admin@email.com', isAdmin: true },
],

// Line 185
if (email === 'your-admin@email.com' && password === 'your-password') {
```

### 📦 Add Book Categories

1. Edit `src/data/books.ts`:
```typescript
export type BookCategory = 'paperback' | 'ebook' | 'audiobook' | 'academic' | 'children' | 'worldLiterature' | 'newCategory';
```

2. Add translations in `src/i18n/translations.ts`:
```typescript
newCategory: 'New Category',
// Arabic
newCategory: 'قسم جديد',
// French
newCategory: 'Nouvelle Catégorie',
```

3. Add category image in `src/data/books.ts`:
```typescript
export const categoryImages: Record<BookCategory, string> = {
  // ... existing
  newCategory: 'https://your-image-url.jpg',
};
```

4. Add icon in `src/components/Categories.tsx` and `src/components/BooksPage.tsx`.

---

## 🇸🇦 العربية

### 🏷️ تغيير اسم المتجر والعلامة التجارية

#### 1. اسم المتجر
عدّل `src/components/Navbar.tsx` سطر 47:
```tsx
<span>كِتاب</span>  // غيّر لاسم متجرك
```

#### 2. عنوان الصفحة
عدّل `index.html`:
```html
<title>اسم متجرك — متجر الكتب الفاخر</title>
```

#### 3. نص "من نحن"
عدّل `src/i18n/translations.ts`:
```typescript
aboutText: 'نص من نحن الخاص بك...',
```

### 🎨 تغيير الألوان

اللون الرئيسي هو **amber-500**. للتغيير:

1. ابحث عن `amber-500`, `amber-400`, `amber-600` في كل الملفات
2. استبدل باللون المفضل (مثل `blue-500`, `emerald-500`)

### 📷 تغيير الصور

#### صورة الهيرو
عدّل `src/components/Hero.tsx` سطر 16

#### صور الأقسام
عدّل `src/data/books.ts` - كائن `categoryImages`

#### صور الكتب
أضف كتب جديدة من لوحة التحكم

### 💰 تغيير العملة

عدّل `src/i18n/translations.ts` لإضافة عملات جديدة.

### 🌍 إضافة لغة جديدة

1. عدّل `src/i18n/translations.ts` وأضف ترجمات اللغة الجديدة
2. حدّث قائمة اللغات في Navbar

### 📱 تغيير بيانات الأدمن

عدّل `src/store/useStore.ts` وغيّر البريد وكلمة المرور.

---

## 🇫🇷 Français

### 🏷️ Changer le Nom & le Branding

#### 1. Nom du Magasin
Modifier `src/components/Navbar.tsx` ligne 47:
```tsx
<span>KITAB</span>  // Changer par votre nom
```

#### 2. Titre de la Page
Modifier `index.html`:
```html
<title>VOTRE NOM — Librairie Premium</title>
```

#### 3. Texte À Propos
Modifier `src/i18n/translations.ts`:
```typescript
aboutText: 'Votre texte personnalisé...',
```

### 🎨 Changer les Couleurs

La couleur principale est **amber-500**. Pour changer:

1. Rechercher `amber-500`, `amber-400`, `amber-600` dans tous les fichiers
2. Remplacer par votre couleur préférée

### 📷 Changer les Images

Modifier les URLs d'images dans les composants correspondants.

### 💰 Changer la Devise

Modifier `src/i18n/translations.ts` pour ajouter de nouvelles devises.

### 🌍 Ajouter une Nouvelle Langue

1. Modifier `src/i18n/translations.ts` et ajouter les traductions
2. Mettre à jour le sélecteur de langue dans Navbar

### 📱 Changer les Identifiants Admin

Modifier `src/store/useStore.ts` et changer l'email et le mot de passe.

---

## 💬 Support

📧 abdulrhmant948@gmail.com

---

**© 2026 KITAB. All rights reserved.**
