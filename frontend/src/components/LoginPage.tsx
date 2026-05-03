import { type FormEvent, useState } from 'react'
import { login, register } from '../services/authService'
import type { AuthUser } from '../types/api'
import './LoginPage.css'

type LoginPageProps = {
  onLogin: (user: AuthUser) => void
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [pending, setPending] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!username.trim() || !password.trim()) return

    setPending(true)
    setErrorText(null)

    try {
      let user: AuthUser
      if (mode === 'login') {
        user = await login({ username: username.trim(), password })
      } else {
        user = await register({ username: username.trim(), password, email: email.trim() || undefined })
      }
      onLogin(user)
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : 'Authentication failed.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="login-page">
      <section className="login-story" aria-label="Assistant overview">
        <span className="login-pill">Light Glass AI Workspace</span>
        <h2>Your ACU questions, answered with context.</h2>
        <p>
          Sign in to continue conversations, review previous sessions, and open cited sources
          without leaving the assistant workspace.
        </p>
        <div className="login-feature-grid">
          <span>Source-aware answers</span>
          <span>Saved sessions</span>
          <span>Fast student guidance</span>
        </div>
      </section>

      <div className="login-card">
        <p className="login-kicker">Welcome</p>
        <h2>{mode === 'login' ? 'Sign in to ACU Assistant' : 'Create your ACU Assistant account'}</h2>

        {errorText && <div className="login-error" role="alert">{errorText}</div>}

        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="auth-username">Username</label>
          <input
            id="auth-username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            minLength={3}
            required
          />

          <label htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            minLength={6}
            required
          />

          {mode === 'register' && (
            <>
              <label htmlFor="auth-email">Email (optional)</label>
              <input
                id="auth-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </>
          )}

          <button type="submit" disabled={pending}>
            {pending ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <p className="login-switch">
          {mode === 'login' ? (
            <>Don't have an account? <button type="button" onClick={() => setMode('register')}>Register</button></>
          ) : (
            <>Already have an account? <button type="button" onClick={() => setMode('login')}>Sign In</button></>
          )}
        </p>

        <p className="login-anon">
          <button type="button" onClick={() => onLogin({ id: 0, username: 'Anonymous', role: 'anonymous' })}>
            Continue as guest
          </button>
        </p>
      </div>
    </div>
  )
}
