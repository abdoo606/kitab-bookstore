# 📖 KITAB Installation Guide / دليل التثبيت / Guide d'Installation

---

## 🇺🇸 English

### Prerequisites
- Node.js 18+ (recommended: 20+)
- npm or yarn

### Installation Steps

1. **Extract the template**
   ```bash
   unzip kitab-template.zip
   cd kitab-template
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Open in browser**
   ```
   http://localhost:5173
   ```

### Build for Production

```bash
npm run build
```

The production files will be in the `dist/` folder.

### Admin Access

- **Email:** admin@kitab.com
- **Password:** admin123

### Customization

#### Change Branding
1. Edit `index.html` - Change title and meta tags
2. Edit `src/components/Navbar.tsx` - Change logo name
3. Edit `src/components/Footer.tsx` - Update footer content

#### Add/Edit Books
1. Login as admin
2. Go to Admin Panel → Manage Products
3. Click "Add Product" or edit existing ones
4. Fill in details in all 3 languages (English, Arabic, French)

#### Change Colors
Edit `src/index.css` or modify Tailwind classes in components.
Main accent color is `amber-500` - search and replace to change.

#### Add New Language
1. Edit `src/i18n/translations.ts`
2. Add new language translations
3. Update language selector in `src/components/Navbar.tsx`

---

## 🇸🇦 العربية

### المتطلبات
- Node.js 18+ (مُوصى به: 20+)
- npm أو yarn

### خطوات التثبيت

1. **فك الضغط**
   ```bash
   unzip kitab-template.zip
   cd kitab-template
   ```

2. **تثبيت الحزم**
   ```bash
   npm install
   ```

3. **تشغيل سيرفر التطوير**
   ```bash
   npm run dev
   ```

4. **فتح في المتصفح**
   ```
   http://localhost:5173
   ```

### بناء للإنتاج

```bash
npm run build
```

ملفات الإنتاج ستكون في مجلد `dist/`

### دخول الأدمن

- **البريد:** admin@kitab.com
- **كلمة المرور:** admin123

### التخصيص

#### تغيير العلامة التجارية
1. عدّل `index.html` - غيّر العنوان والوصف
2. عدّل `src/components/Navbar.tsx` - غيّر اسم الشعار
3. عدّل `src/components/Footer.tsx` - حدّث محتوى الفوتر

#### إضافة/تعديل الكتب
1. سجّل دخول كأدمن
2. اذهب للوحة التحكم ← إدارة المنتجات
3. اضغط "إضافة منتج" أو عدّل الموجودين
4. املأ التفاصيل بالـ 3 لغات (إنجليزي، عربي، فرنسي)

#### تغيير الألوان
عدّل `src/index.css` أو كلاسات Tailwind في المكونات.
اللون الرئيسي هو `amber-500` - ابحث واستبدل للتغيير.

#### إضافة لغة جديدة
1. عدّل `src/i18n/translations.ts`
2. أضف ترجمات اللغة الجديدة
3. حدّث قائمة اللغات في `src/components/Navbar.tsx`

---

## 🇫🇷 Français

### Prérequis
- Node.js 18+ (recommandé: 20+)
- npm ou yarn

### Étapes d'Installation

1. **Extraire le template**
   ```bash
   unzip kitab-template.zip
   cd kitab-template
   ```

2. **Installer les dépendances**
   ```bash
   npm install
   ```

3. **Lancer le serveur de développement**
   ```bash
   npm run dev
   ```

4. **Ouvrir dans le navigateur**
   ```
   http://localhost:5173
   ```

### Build pour Production

```bash
npm run build
```

Les fichiers de production seront dans le dossier `dist/`

### Accès Admin

- **Email:** admin@kitab.com
- **Mot de passe:** admin123

### Personnalisation

#### Changer le Branding
1. Modifier `index.html` - Changer le titre et les méta tags
2. Modifier `src/components/Navbar.tsx` - Changer le nom du logo
3. Modifier `src/components/Footer.tsx` - Mettre à jour le contenu du footer

#### Ajouter/Modifier des Livres
1. Se connecter en tant qu'admin
2. Aller au Panneau Admin → Gérer les Produits
3. Cliquer sur "Ajouter un Produit" ou modifier les existants
4. Remplir les détails dans les 3 langues (Anglais, Arabe, Français)

#### Changer les Couleurs
Modifier `src/index.css` ou les classes Tailwind dans les composants.
La couleur principale est `amber-500` - rechercher et remplacer pour changer.

#### Ajouter une Nouvelle Langue
1. Modifier `src/i18n/translations.ts`
2. Ajouter les traductions de la nouvelle langue
3. Mettre à jour le sélecteur de langue dans `src/components/Navbar.tsx`

---

## 🛠️ File Structure / هيكل الملفات / Structure des Fichiers

```
kitab-template/
├── public/                 # Static assets
├── src/
│   ├── components/         # React components
│   │   ├── AdminDashboard.tsx
│   │   ├── AuthPage.tsx
│   │   ├── BookCard.tsx
│   │   ├── BookFormModal.tsx
│   │   ├── BookModal.tsx
│   │   ├── BooksPage.tsx
│   │   ├── CartSidebar.tsx
│   │   ├── Categories.tsx
│   │   ├── CheckoutPage.tsx
│   │   ├── FeaturedBooks.tsx
│   │   ├── Footer.tsx
│   │   ├── Hero.tsx
│   │   ├── Navbar.tsx
│   │   ├── OrdersPage.tsx
│   │   ├── OrderSuccess.tsx
│   │   └── PromoBanner.tsx
│   ├── data/
│   │   └── books.ts        # Sample book data
│   ├── hooks/
│   │   └── useTranslation.ts
│   ├── i18n/
│   │   └── translations.ts # All translations
│   ├── store/
│   │   └── useStore.ts     # Zustand state management
│   ├── utils/
│   │   └── cn.ts           # Utility functions
│   ├── App.tsx             # Main app component
│   ├── index.css           # Global styles
│   └── main.tsx            # Entry point
├── index.html
├── package.json
├── README.md
├── LICENSE
├── INSTALLATION.md
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## 💬 Support

📧 abdulrhmant948@gmail.com

---

**© 2026 KITAB. All rights reserved.**
