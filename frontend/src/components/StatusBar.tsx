type StatusBarProps = {
  errorText: string | null
  retryAfter: number | null
}

export function StatusBar({ errorText, retryAfter }: StatusBarProps) {
  const hasContent = Boolean(errorText || retryAfter)

  return (
    <aside
      className="status-bar"
      role="alert"
      style={{ display: hasContent ? 'flex' : 'none' }}
    >
      {errorText && <span>{errorText}</span>}
      {retryAfter && <span>Retry after {retryAfter}s</span>}
    </aside>
  )
}
