import React, { useEffect, useState, useCallback, createContext, useContext, useRef } from 'react';
import { X, CheckCircle2, AlertCircle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'motion/react';

type ToastVariant = 'success' | 'error' | 'info';

interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (message: string, variant?: ToastVariant) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let toastCounter = 0;

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

export const toast = {
  success: (message: string) => {
    const ctx = getGlobalToastContext();
    ctx?.addToast(message, 'success');
  },
  error: (message: string) => {
    const ctx = getGlobalToastContext();
    ctx?.addToast(message, 'error');
  },
  info: (message: string) => {
    const ctx = getGlobalToastContext();
    ctx?.addToast(message, 'info');
  },
};

// Global ref so the standalone `toast` object can work outside React tree
let globalToastRef: React.RefObject<ToastContextValue | null> = { current: null };
function getGlobalToastContext() {
  return globalToastRef.current;
}

const variantStyles: Record<ToastVariant, { bg: string; border: string; text: string; icon: React.ElementType }> = {
  success: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-800', icon: CheckCircle2 },
  error: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', icon: AlertCircle },
  info: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', icon: Info },
};

function ToastItem({ toast: t, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const [_isExiting, setIsExiting] = useState(false);
  const styles = variantStyles[t.variant];
  const Icon = styles.icon;

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(onDismiss, 300);
    }, 3000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 80, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.95 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg min-w-[300px] max-w-[420px]',
        styles.bg,
        styles.border
      )}
    >
      <Icon className={cn('w-5 h-5 shrink-0', styles.text)} />
      <p className={cn('text-sm font-medium flex-1', styles.text)}>{t.message}</p>
      <button
        onClick={() => {
          setIsExiting(true);
          setTimeout(onDismiss, 300);
        }}
        className={cn('shrink-0 p-0.5 rounded-md hover:bg-black/5 transition-colors', styles.text)}
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const addToast = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = `toast-${++toastCounter}`;
    setToasts((prev) => [...prev, { id, message, variant }]);
  }, []);
  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  globalToastRef = useRef({ toasts, addToast, removeToast });
  // Keep ref current
  globalToastRef.current = { toasts, addToast, removeToast };

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((t) => (
            <ToastItem key={t.id} toast={t} onDismiss={() => removeToast(t.id)} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
