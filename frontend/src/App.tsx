import type { FormEvent } from 'react'
import type { Citation } from './types/api'
import { useChat } from './hooks/useChat'
import { ConversationPanel } from './components/ConversationPanel'
import { LoginPage } from './components/LoginPage'
import { Masthead } from './components/Masthead'
import { SessionSidebar } from './components/SessionSidebar'
import { SourcePanel } from './components/SourcePanel'
import { StatusBar } from './components/StatusBar'
import './App.css'

function App() {
  const {
    question,
    setQuestion,
    sessionId,
    authUser,
    pending,
    sortedMessages,
    errorText,
    retryAfter,
    feedbackReasonByMessage,
    setFeedbackReasonByMessage,
    feedbackCommentByMessage,
    setFeedbackCommentByMessage,
    submittedFeedback,
    sourceLoading,
    selectedSource,
    submitQuestion,
    submitFeedback,
    loadSource,
    handleLogin,
    handleLogout,
    startNewChat,
    switchSession,
  } = useChat()

  if (!authUser) {
    return (
      <div className="app-shell auth-shell">
        <Masthead />
        <LoginPage onLogin={handleLogin} />
      </div>
    )
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await submitQuestion()
  }

  async function handleFeedback(messageId: string, rating: 'up' | 'down') {
    await submitFeedback(messageId, rating)
  }

  async function handleCitationClick(citation: Citation) {
    await loadSource(citation)
  }

  return (
    <div className="app-shell-fluid">
      <aside className="sidebar-column">
        <SessionSidebar
          currentSessionId={sessionId}
          onSelectSession={(id) => void switchSession(id)}
          onNewChat={startNewChat}
        />
      </aside>

      <main className="main-column">
        <header className="topbar">
          <Masthead />
          <div className="account-card" aria-label="Account status">
            <span className="account-kicker">Signed in</span>
            <strong>{authUser.username}</strong>
            <button type="button" onClick={() => void handleLogout()}>Sign out</button>
          </div>
        </header>

        <div className="workspace">
          <section className="content-column">
            <ConversationPanel
              sessionId={sessionId}
              sortedMessages={sortedMessages}
              sourceLoading={sourceLoading}
              feedbackReasonByMessage={feedbackReasonByMessage}
              setFeedbackReasonByMessage={setFeedbackReasonByMessage}
              feedbackCommentByMessage={feedbackCommentByMessage}
              setFeedbackCommentByMessage={setFeedbackCommentByMessage}
              submittedFeedback={submittedFeedback}
              handleCitationClick={handleCitationClick}
              handleFeedback={handleFeedback}
              question={question}
              setQuestion={setQuestion}
              pending={pending}
              handleSubmit={handleSubmit}
            />
          </section>

          <aside className="evidence-column">
            <SourcePanel sourceLoading={sourceLoading} selectedSource={selectedSource} />
          </aside>
        </div>

        <StatusBar errorText={errorText} retryAfter={retryAfter} />
      </main>
    </div>
  )
}

export default App
