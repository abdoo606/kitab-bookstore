# 🚀 Deployment Guide / دليل النشر / Guide de Déploiement

---

## 🇺🇸 English

### 📦 Step 1: Prepare Your Project

Make sure you have all files ready:
```bash
# Install dependencies (if not done)
npm install

# Test build locally
npm run build

# Preview locally (optional)
npm run preview
```

---

### 🐙 Step 2: Upload to GitHub

#### Option A: Using GitHub Website (Easiest)

1. **Go to GitHub**: https://github.com
2. **Login** or create account
3. **Click** the green **"New"** button (or go to https://github.com/new)
4. **Repository name**: `kitab-bookstore` (or any name)
5. **Choose**: Public or Private
6. **Click**: "Create repository"

7. **Upload files**:
   - Click **"uploading an existing file"**
   - Drag and drop ALL your project files (except `node_modules` and `dist` folders)
   - Click **"Commit changes"**

#### Option B: Using Git Command Line

```bash
# 1. Initialize Git (run once)
git init

# 2. Add all files
git add .

# 3. Commit
git commit -m "Initial commit - KITAB Bookstore"

# 4. Add GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/kitab-bookstore.git

# 5. Push to GitHub
git branch -M main
git push -u origin main
```

---

### 🌐 Step 3: Deploy to Netlify

#### Option A: Connect GitHub (Recommended - Auto Deploy)

1. **Go to Netlify**: https://app.netlify.com
2. **Login** with GitHub
3. **Click**: "Add new site" → "Import an existing project"
4. **Choose**: "Deploy with GitHub"
5. **Authorize** Netlify to access your GitHub
6. **Select** your repository: `kitab-bookstore`
7. **Configure build settings**:
   - Build command: `npm run build`
   - Publish directory: `dist`
8. **Click**: "Deploy site"
9. **Wait** 1-2 minutes for deployment
10. **Your site is live!** 🎉

#### Option B: Drag & Drop (Quick Deploy)

1. **Build locally**:
   ```bash
   npm run build
   ```

2. **Go to**: https://app.netlify.com/drop

3. **Drag** the `dist` folder and drop it

4. **Done!** Your site is live instantly

---

### 🔗 Step 4: Custom Domain (Optional)

1. In Netlify dashboard, go to **"Domain settings"**
2. Click **"Add custom domain"**
3. Enter your domain: `www.kitab-store.com`
4. Follow DNS setup instructions
5. Enable **HTTPS** (free SSL certificate)

---

### 🔄 Auto Deploy (with GitHub)

After connecting GitHub:
- Every time you push to `main` branch
- Netlify automatically rebuilds and deploys
- Changes go live in ~1 minute

```bash
# Make changes, then:
git add .
git commit -m "Update: added new feature"
git push
# Netlify deploys automatically!
```

---

## 🇸🇦 العربية

### 📦 الخطوة 1: تجهيز المشروع

```bash
# تثبيت الحزم
npm install

# اختبار البناء محلياً
npm run build
```

---

### 🐙 الخطوة 2: الرفع على GitHub

#### الطريقة أ: من موقع GitHub (الأسهل)

1. **اذهب لـ**: https://github.com
2. **سجّل دخول** أو أنشئ حساب
3. **اضغط** على زر **"New"** الأخضر
4. **اسم المستودع**: `kitab-bookstore`
5. **اختر**: Public أو Private
6. **اضغط**: "Create repository"
7. **ارفع الملفات**:
   - اضغط **"uploading an existing file"**
   - اسحب كل ملفات المشروع (ما عدا `node_modules` و `dist`)
   - اضغط **"Commit changes"**

#### الطريقة ب: باستخدام Git

```bash
# 1. تهيئة Git
git init

# 2. إضافة الملفات
git add .

# 3. حفظ التغييرات
git commit -m "Initial commit - KITAB Bookstore"

# 4. ربط GitHub (غيّر YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/kitab-bookstore.git

# 5. رفع للـ GitHub
git branch -M main
git push -u origin main
```

---

### 🌐 الخطوة 3: النشر على Netlify

#### الطريقة أ: ربط GitHub (موصى بها)

1. **اذهب لـ**: https://app.netlify.com
2. **سجّل** بحساب GitHub
3. **اضغط**: "Add new site" → "Import an existing project"
4. **اختر**: "Deploy with GitHub"
5. **اختر** مستودعك: `kitab-bookstore`
6. **إعدادات البناء**:
   - Build command: `npm run build`
   - Publish directory: `dist`
7. **اضغط**: "Deploy site"
8. **انتظر** 1-2 دقيقة
9. **موقعك جاهز!** 🎉

#### الطريقة ب: سحب وإفلات (نشر سريع)

1. **ابني محلياً**:
   ```bash
   npm run build
   ```
2. **اذهب لـ**: https://app.netlify.com/drop
3. **اسحب** مجلد `dist` وأفلته
4. **تم!** موقعك جاهز فوراً

---

### 🔄 النشر التلقائي

بعد ربط GitHub:
- كل ما ترفع تحديث على `main`
- Netlify تعيد البناء والنشر تلقائياً
- التغييرات تظهر خلال دقيقة

```bash
# عدّل ثم:
git add .
git commit -m "تحديث: ميزة جديدة"
git push
# Netlify تنشر تلقائياً!
```

---

## 🇫🇷 Français

### 📦 Étape 1: Préparer le Projet

```bash
# Installer les dépendances
npm install

# Tester le build localement
npm run build
```

---

### 🐙 Étape 2: Télécharger sur GitHub

1. **Allez sur**: https://github.com
2. **Connectez-vous**
3. **Cliquez** sur **"New"**
4. **Nom du repo**: `kitab-bookstore`
5. **Cliquez**: "Create repository"
6. **Téléchargez** tous les fichiers (sauf `node_modules` et `dist`)

---

### 🌐 Étape 3: Déployer sur Netlify

1. **Allez sur**: https://app.netlify.com
2. **Connectez-vous** avec GitHub
3. **Cliquez**: "Add new site" → "Import an existing project"
4. **Sélectionnez** votre repo
5. **Paramètres**:
   - Build command: `npm run build`
   - Publish directory: `dist`
6. **Cliquez**: "Deploy site"
7. **Votre site est en ligne!** 🎉

---

## 📋 Quick Reference / مرجع سريع

| Platform | URL |
|----------|-----|
| GitHub | https://github.com |
| Netlify | https://app.netlify.com |
| Netlify Drop | https://app.netlify.com/drop |

### Build Settings:
```
Build command: npm run build
Publish directory: dist
Node version: 18+ (or 20)
```

### Environment Variables (if needed):
```
NODE_VERSION = 20
```

---

## 🆘 Troubleshooting / حل المشاكل

### Build fails on Netlify?

1. Check Node version - add in Netlify:
   - Environment variable: `NODE_VERSION` = `20`

2. Check package.json has all dependencies

3. Try building locally first:
   ```bash
   npm run build
   ```

### 404 errors on page refresh?

Make sure `netlify.toml` file exists with redirect rules (already included).

### Images not loading?

Check image URLs are using HTTPS and are accessible.

---

## 💬 Support

📧 abdulrhmant948@gmail.com

---

**© 2026 KITAB. All rights reserved.**
