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
      <div className="page">
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
    <main className="page">
      <Masthead />

      <div className="auth-bar">
        <span>Signed in as: {authUser.username}</span>
        <button type="button" onClick={() => void handleLogout()}>Sign Out</button>
      </div>

      <div className="main-layout">
        <aside className="sidebar-column">
          <SessionSidebar
            currentSessionId={sessionId}
            onSelectSession={(id) => void switchSession(id)}
            onNewChat={startNewChat}
          />
        </aside>

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
      </div>

      <SourcePanel sourceLoading={sourceLoading} selectedSource={selectedSource} />

      <StatusBar errorText={errorText} retryAfter={retryAfter} />
    </main>
  )
}

export default App
