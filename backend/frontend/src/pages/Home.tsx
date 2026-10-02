import { motion } from 'framer-motion'
import { ArrowRight, KeyRound, Lock, Mail, Mic, Sparkles } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../hooks/useSession'
import { Button, Field } from '../components/ui'
import { homeFor, signIn } from '../lib/session'

export default function Home() {
  const navigate = useNavigate()
  const session = useSession()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (session) navigate(homeFor(session.role), { replace: true })
  }, [session, navigate])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const staff = await signIn(email, password)
      navigate(homeFor(staff.role))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reach the server. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Decorative background blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-96 w-96 rounded-full bg-gradient-to-br from-primary/20 to-primary-to/10 blur-3xl" />
        <div className="absolute -right-32 top-40 h-80 w-80 rounded-full bg-gradient-to-br from-violet/15 to-primary/10 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-gradient-to-br from-safe/10 to-info/10 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-5xl flex-col px-5 py-10 sm:px-8">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12 inline-flex w-fit items-center gap-2 self-center rounded-full border border-border bg-white px-4 py-1.5 text-xs font-semibold text-primary-dark shadow-xs sm:self-start"
        >
          <Sparkles size={13} />
          Vernacular Voice-to-SOP
        </motion.div>

        <div className="flex flex-1 flex-col items-center justify-center gap-14">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="max-w-2xl text-center"
          >
            <h1 className="text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
              Say the procedure.
              <br />
              <span className="bg-gradient-to-br from-primary to-primary-to bg-clip-text text-transparent">
                Get picture-and-voice cards.
              </span>
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-balance text-lg text-ink-soft">
              A supervisor narrates a procedure in Hindi or Marathi. The machine shows it as cards a
              worker can hear — and hears the worker back.
            </p>
          </motion.div>

          <div className="grid w-full max-w-3xl gap-6 sm:grid-cols-5">
            <motion.a
              href="#/machines"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.12 }}
              whileHover={{ y: -4 }}
              className="group relative overflow-hidden rounded-3xl border border-border bg-white p-8 shadow-md transition-shadow hover:shadow-lg sm:col-span-3"
            >
              <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br from-primary/10 to-primary-to/10 transition-transform duration-500 group-hover:scale-125" />
              <div className="relative flex items-start gap-5">
                <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-to text-white shadow-glow">
                  <Mic size={30} />
                </div>
                <div>
                  <h2 className="lang-dev text-3xl font-bold text-ink">कामगार</h2>
                  <p className="lang-dev mt-1.5 text-lg leading-snug text-ink-soft">
                    अपनी मशीन के कार्ड देखें और सुनें। कुछ कहना हो तो बोलें।
                  </p>
                  <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-primary-dark">
                    Enter without signing in
                    <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" />
                  </span>
                </div>
              </div>
            </motion.a>

            <motion.form
              onSubmit={handleSubmit}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.18 }}
              className="flex flex-col rounded-3xl border border-border bg-white p-7 shadow-md sm:col-span-2"
            >
              <h2 className="text-base font-bold text-ink">Supervisor or manager</h2>
              <p className="mt-1 text-xs leading-relaxed text-ink-soft">
                Workers do not sign in. Staff do, so a card is only written by whoever runs that line.
              </p>

              <div className="mt-5 flex flex-col gap-3">
                <div className="relative">
                  <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint" />
                  <Field
                    type="email"
                    required
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <div className="relative">
                  <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint" />
                  <Field
                    type="password"
                    required
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Button type="submit" loading={loading} className="mt-1 w-full">
                  {!loading && <KeyRound size={16} />}
                  Sign in
                </Button>
              </div>

              {error && (
                <motion.p
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mt-3 rounded-xl bg-stop-bg px-3 py-2 text-xs font-medium text-stop"
                >
                  {error}
                </motion.p>
              )}
            </motion.form>
          </div>
        </div>
      </div>
    </div>
  )
}
