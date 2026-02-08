import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { hasError: boolean; error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="screen-center" style={{ padding: 24, textAlign: 'center' }}>
          <span className="empty-icon" style={{ fontSize: 48 }}>⚠️</span>
          <p style={{ marginTop: 12 }}>Что-то пошло не так</p>
          <p className="text-muted" style={{ fontSize: 14, marginTop: 8 }}>
            {this.state.error?.message || 'Ошибка загрузки'}
          </p>
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: 16 }}
            onClick={() => window.location.replace('/')}
          >
            На главную
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
