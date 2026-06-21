import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Language, Currency } from '../i18n/translations';
import type { Book, BookCategory } from '../data/books';
import { books as initialBooks } from '../data/books';

export interface CartItem {
  book: Book;
  quantity: number;
}

export interface User {
  id: string;
  name: string;
  email: string;
  isAdmin: boolean;
}

export interface Order {
  id: string;
  userId: string;
  items: CartItem[];
  total: number;
  currency: Currency;
  status: 'pending' | 'processing' | 'shipped' | 'delivered';
  date: string;
  shippingInfo: {
    fullName: string;
    email: string;
    phone: string;
    address: string;
    city: string;
    country: string;
  };
  paymentMethod: string;
}

type Page = 'home' | 'books' | 'newArrivals' | 'offers' | 'cart' | 'checkout' | 'login' | 'register' | 'admin' | 'orders' | 'orderSuccess';

interface AppState {
  // Theme
  isDark: boolean;
  toggleTheme: () => void;
  
  // Language & Currency
  language: Language;
  currency: Currency;
  setLanguage: (lang: Language) => void;
  setCurrency: (curr: Currency) => void;
  
  // Navigation
  currentPage: Page;
  setPage: (page: Page) => void;
  
  // Category filter
  selectedCategory: BookCategory | 'all';
  setCategory: (cat: BookCategory | 'all') => void;
  
  // Search
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  
  // Books Management
  books: Book[];
  addBook: (book: Omit<Book, 'id'>) => void;
  updateBook: (id: string, book: Partial<Book>) => void;
  deleteBook: (id: string) => void;
  
  // Cart
  cart: CartItem[];
  addToCart: (book: Book) => void;
  removeFromCart: (bookId: string) => void;
  updateQuantity: (bookId: string, quantity: number) => void;
  clearCart: () => void;
  
  // Auth
  user: User | null;
  users: User[];
  loginUser: (email: string, password: string) => boolean;
  registerUser: (name: string, email: string, password: string) => boolean;
  logoutUser: () => void;
  
  // Orders
  orders: Order[];
  addOrder: (order: Omit<Order, 'id' | 'date' | 'status'>) => void;
  updateOrderStatus: (orderId: string, status: Order['status']) => void;
  
  // Product modal
  selectedBook: Book | null;
  setSelectedBook: (book: Book | null) => void;
  
  // Edit book modal
  editingBook: Book | null;
  setEditingBook: (book: Book | null) => void;
  
  // Cart sidebar
  isCartOpen: boolean;
  setCartOpen: (open: boolean) => void;
  
  // Mobile menu
  isMobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  
  // Add book modal
  isAddBookModalOpen: boolean;
  setAddBookModalOpen: (open: boolean) => void;
}

// Store passwords separately (in real app, use proper auth)
const passwords: Record<string, string> = {
  'admin@kitab.com': 'admin123',
};

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Theme
      isDark: false,
      toggleTheme: () => set((state) => ({ isDark: !state.isDark })),
      
      // Language & Currency
      language: 'ar',
      currency: 'USD',
      setLanguage: (language) => set({ language }),
      setCurrency: (currency) => set({ currency }),
      
      // Navigation
      currentPage: 'home',
      setPage: (currentPage) => set({ currentPage, isMobileMenuOpen: false }),
      
      // Category
      selectedCategory: 'all',
      setCategory: (selectedCategory) => set({ selectedCategory }),
      
      // Search
      searchQuery: '',
      setSearchQuery: (searchQuery) => set({ searchQuery }),
      
      // Books Management
      books: initialBooks,
      addBook: (bookData) => set((state) => {
        const newBook: Book = {
          ...bookData,
          id: 'book-' + Date.now().toString(),
        };
        return { books: [...state.books, newBook] };
      }),
      updateBook: (id, bookData) => set((state) => ({
        books: state.books.map((b) => b.id === id ? { ...b, ...bookData } : b),
      })),
      deleteBook: (id) => set((state) => ({
        books: state.books.filter((b) => b.id !== id),
        cart: state.cart.filter((item) => item.book.id !== id),
      })),
      
      // Cart
      cart: [],
      addToCart: (book) => set((state) => {
        const existing = state.cart.find((item) => item.book.id === book.id);
        if (existing) {
          return {
            cart: state.cart.map((item) =>
              item.book.id === book.id
                ? { ...item, quantity: item.quantity + 1 }
                : item
            ),
          };
        }
        return { cart: [...state.cart, { book, quantity: 1 }] };
      }),
      removeFromCart: (bookId) => set((state) => ({
        cart: state.cart.filter((item) => item.book.id !== bookId),
      })),
      updateQuantity: (bookId, quantity) => set((state) => ({
        cart: quantity <= 0
          ? state.cart.filter((item) => item.book.id !== bookId)
          : state.cart.map((item) =>
              item.book.id === bookId ? { ...item, quantity } : item
            ),
      })),
      clearCart: () => set({ cart: [] }),
      
      // Auth
      user: null,
      users: [
        { id: '1', name: 'Admin', email: 'admin@kitab.com', isAdmin: true },
      ],
      loginUser: (email, password) => {
        const state = get();
        // Check admin
        if (email === 'admin@kitab.com' && password === 'admin123') {
          const adminUser = state.users.find((u) => u.email === 'admin@kitab.com');
          if (adminUser) {
            set({ user: adminUser });
            return true;
          }
        }
        // Check registered users
        const storedPass = passwords[email];
        if (storedPass === password) {
          const user = state.users.find((u) => u.email === email);
          if (user) {
            set({ user });
            return true;
          }
        }
        return false;
      },
      registerUser: (name, email, password) => {
        const state = get();
        if (state.users.find((u) => u.email === email)) return false;
        const newUser: User = {
          id: Date.now().toString(),
          name,
          email,
          isAdmin: false,
        };
        passwords[email] = password;
        set({ users: [...state.users, newUser], user: newUser });
        return true;
      },
      logoutUser: () => set({ user: null, currentPage: 'home' }),
      
      // Orders
      orders: [],
      addOrder: (orderData) => set((state) => {
        const newOrder: Order = {
          ...orderData,
          id: 'ORD-' + Date.now().toString().slice(-6),
          date: new Date().toISOString(),
          status: 'pending',
        };
        return { orders: [...state.orders, newOrder] };
      }),
      updateOrderStatus: (orderId, status) => set((state) => ({
        orders: state.orders.map((o) =>
          o.id === orderId ? { ...o, status } : o
        ),
      })),
      
      // Product modal
      selectedBook: null,
      setSelectedBook: (selectedBook) => set({ selectedBook }),
      
      // Edit book modal
      editingBook: null,
      setEditingBook: (editingBook) => set({ editingBook }),
      
      // Cart sidebar
      isCartOpen: false,
      setCartOpen: (isCartOpen) => set({ isCartOpen }),
      
      // Mobile menu
      isMobileMenuOpen: false,
      setMobileMenuOpen: (isMobileMenuOpen) => set({ isMobileMenuOpen }),
      
      // Add book modal
      isAddBookModalOpen: false,
      setAddBookModalOpen: (isAddBookModalOpen) => set({ isAddBookModalOpen }),
    }),
    {
      name: 'kitab-store',
      partialize: (state) => ({
        isDark: state.isDark,
        language: state.language,
        currency: state.currency,
        cart: state.cart,
        user: state.user,
        users: state.users,
        orders: state.orders,
        books: state.books,
      }),
    }
  )
);
