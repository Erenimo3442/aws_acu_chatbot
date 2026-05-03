import type { Dispatch, FormEvent, SetStateAction } from 'react'
import type { FeedbackReason, UiMessage } from '../models/chat'
import type { Citation } from '../types/api'
import { formatDateTime } from '../utils/dateTime'
import { MessageCitations } from './MessageCitations'
import { MessageFeedback } from './MessageFeedback'

type ConversationPanelProps = {
  sessionId: string | null
  sortedMessages: UiMessage[]
  sourceLoading: boolean
  feedbackReasonByMessage: Record<string, FeedbackReason>
  setFeedbackReasonByMessage: Dispatch<SetStateAction<Record<string, FeedbackReason>>>
  feedbackCommentByMessage: Record<string, string>
  setFeedbackCommentByMessage: Dispatch<SetStateAction<Record<string, string>>>
  submittedFeedback: Record<string, 'up' | 'down'>
  handleCitationClick: (citation: Citation) => Promise<void>
  handleFeedback: (messageId: string, rating: 'up' | 'down') => Promise<void>
  question: string
  setQuestion: Dispatch<SetStateAction<string>>
  pending: boolean
  handleSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>
}

const promptSuggestions = [
  'What are the application deadlines for new students?',
  'How much is tuition for this semester?',
  'Which documents do I need for admission?',
  'Where can I find academic calendar dates?',
]

export function ConversationPanel({
  sessionId,
  sortedMessages,
  sourceLoading,
  feedbackReasonByMessage,
  setFeedbackReasonByMessage,
  feedbackCommentByMessage,
  setFeedbackCommentByMessage,
  submittedFeedback,
  handleCitationClick,
  handleFeedback,
  question,
  setQuestion,
  pending,
  handleSubmit,
}: ConversationPanelProps) {
  const hasMessages = sortedMessages.length > 0

  return (
    <section className="panel chat-panel" aria-live="polite">
      <div className="panel-head">
        <div>
          <h2>{hasMessages ? 'Conversation' : 'Ask ACU Assistant'}</h2>
          <p>{sessionId ? `Session: ${sessionId}` : 'A session will be created when you send your first message.'}</p>
        </div>
      </div>

      {!hasMessages ? (
        <div className="chat-intro">
          <div className="chat-intro-card">
            <div className="assistant-orb" aria-hidden="true" />
            <h2>What do you need to know today?</h2>
            <p>
              Ask about admissions, fees, academic dates, program details, or student services.
              I will answer with source-aware context when citations are available.
            </p>
            <div className="prompt-chips" aria-label="Suggested questions">
              {promptSuggestions.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="prompt-chip"
                  onClick={() => setQuestion(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="message-list">
          {sortedMessages.map((message) => (
            <article key={message.id} className={`message message-${message.role}`}>
              <div className="message-meta">
                <span>{message.role.toUpperCase()}</span>
                <time dateTime={message.createdAt}>{formatDateTime(message.createdAt)}</time>
              </div>
              <p>{message.content}</p>

              <MessageCitations
                citations={message.citations}
                sourceLoading={sourceLoading}
                onCitationClick={handleCitationClick}
              />

              {message.role === 'assistant' && (
                <MessageFeedback
                  messageId={message.id}
                  feedbackReasonByMessage={feedbackReasonByMessage}
                  setFeedbackReasonByMessage={setFeedbackReasonByMessage}
                  feedbackCommentByMessage={feedbackCommentByMessage}
                  setFeedbackCommentByMessage={setFeedbackCommentByMessage}
                  submittedFeedback={submittedFeedback}
                  onFeedback={handleFeedback}
                />
              )}
            </article>
          ))}
        </div>
      )}

      <form className="composer" onSubmit={(event) => void handleSubmit(event)}>
        <label htmlFor="question-input" className="caption">
          Message ACU Assistant
        </label>
        <textarea
          id="question-input"
          rows={3}
          value={question}
          maxLength={4000}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about admissions, tuition, schedules, deadlines, or student services..."
        />
        <div className="composer-row">
          <span>{question.trim().length}/4000 characters</span>
          <button type="submit" disabled={pending || !question.trim()}>
            {pending ? 'Thinking...' : 'Send message'}
          </button>
        </div>
      </form>
    </section>
  )
}
