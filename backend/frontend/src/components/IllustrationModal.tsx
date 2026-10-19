import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { StepIllustrationArt } from './StepIllustration'
import type { Step } from '../lib/types'

export function IllustrationModal({ step, onClose }: { step: (Pick<Step, 'icon' | 'is_safety_warning' | 'text' | 'step_number'>) | null; onClose: () => void }) {
  return (
    <AnimatePresence>
      {step && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-5 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 340, damping: 28 }}
            className="w-full max-w-sm overflow-hidden rounded-3xl bg-white shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative">
              <StepIllustrationArt icon={step.icon} is_safety_warning={step.is_safety_warning} />
              <button
                onClick={onClose}
                aria-label="बंद करें"
                className="absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-ink shadow-md"
              >
                <X size={18} />
              </button>
            </div>
            <div className="p-5">
              <p className="lang-dev text-lg leading-snug text-ink" dir="auto">
                {step.text}
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
