import { useEffect, useState } from 'react'
import { getSessionList, postCreateSession, type SessionListItem } from '../lib/apiClient'
import './SessionSidebar.css'

type SessionSidebarProps = {
  currentSessionId: string | null
  onSelectSession: (sessionId: string) => void
  onNewChat: () => void
}

export function SessionSidebar({ currentSessionId, onSelectSession, onNewChat }: SessionSidebarProps) {
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [loading, setLoading] = useState(false)

  async function loadSessions() {
    setLoading(true)
    try {
      const data = await getSessionList()
      setSessions(data.sessions)
    } catch {
      // Silent fail — sidebar is best-effort
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSessions()
  }, [currentSessionId])

  async function handleNewChat() {
    try {
      await postCreateSession()
      onNewChat()
      setTimeout(() => { void loadSessions() }, 300)
    } catch {
      // Fall back to client-side new chat
      onNewChat()
    }
  }

  return (
    <aside className="session-sidebar">
      <div className="sidebar-header">
        <h3>Sessions</h3>
        <button type="button" className="btn-new-chat" onClick={() => void handleNewChat()}>
          + New Chat
        </button>
      </div>

      {loading && <p className="sidebar-loading">Loading...</p>}

      <ul className="session-list">
        {sessions.map((session) => (
          <li
            key={session.id}
            className={`session-item ${session.id === currentSessionId ? 'session-active' : ''}`}
          >
            <button
              type="button"
              onClick={() => onSelectSession(session.id)}
              title={session.id}
            >
              <span className="session-id">{session.id.slice(0, 16)}...</span>
              <span className="session-preview">{session.last_message_preview.slice(0, 60) || 'Empty'}</span>
            </button>
          </li>
        ))}
        {sessions.length === 0 && !loading && (
          <p className="sidebar-empty">No sessions yet</p>
        )}
      </ul>
    </aside>
  )
}
