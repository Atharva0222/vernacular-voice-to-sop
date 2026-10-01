import clsx from 'clsx'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react'
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

type ToastKind = 'error' | 'success' | 'info'
interface ToastItem {
  id: number
  kind: ToastKind
  message: string
}

type PushToast = (kind: ToastKind, message: string) => void

const ToastContext = createContext<PushToast>(() => {})

export function useToast() {
  return useContext(ToastContext)
}

const ICONS: Record<ToastKind, typeof Info> = { error: AlertCircle, success: CheckCircle2, info: Info }
const ICON_WRAP: Record<ToastKind, string> = {
  error: 'bg-stop-bg text-stop',
  success: 'bg-safe-bg text-safe',
  info: 'bg-primary-light text-primary-dark',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const push = useCallback<PushToast>((kind, message) => {
    const id = Date.now() + Math.random()
    setItems((prev) => [...prev, { id, kind, message }])
    setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), 5500)
  }, [])

  const dismiss = (id: number) => setItems((prev) => prev.filter((t) => t.id !== id))

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-5 sm:items-end">
        <AnimatePresence>
          {items.map((t) => {
            const Icon = ICONS[t.kind]
            return (
              <motion.div
                key={t.id}
                layout
                initial={{ opacity: 0, y: 16, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 60, scale: 0.9, transition: { duration: 0.2 } }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                className="pointer-events-auto flex w-[min(92vw,380px)] items-start gap-3 rounded-2xl border border-border bg-white px-4 py-3.5 shadow-lg"
              >
                <span className={clsx('flex h-7 w-7 shrink-0 items-center justify-center rounded-full', ICON_WRAP[t.kind])}>
                  <Icon size={15} />
                </span>
                <p className="flex-1 pt-0.5 text-sm font-medium leading-snug text-ink">{t.message}</p>
                <button
                  onClick={() => dismiss(t.id)}
                  className="rounded-full p-1 text-ink-faint hover:bg-black/5 hover:text-ink"
                  aria-label="Dismiss"
                >
                  <X size={14} />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
