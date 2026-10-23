import { Component, type ErrorInfo, type ReactNode } from 'react';

import type { MessageKey } from '../i18n';

interface ApplicationErrorBoundaryProps {
  children: ReactNode;
  text: (key: MessageKey) => string;
}

interface ApplicationErrorBoundaryState {
  hasError: boolean;
}

export class ApplicationErrorBoundary extends Component<
  ApplicationErrorBoundaryProps,
  ApplicationErrorBoundaryState
> {
  state: ApplicationErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ApplicationErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('The page could not be rendered.', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="account-state-page" id="main-content">
          <section className="account-state-card" role="alert">
            <h1>{this.props.text('pageRenderErrorTitle')}</h1>
            <p>{this.props.text('pageRenderErrorBody')}</p>
            <button
              className="button button-outline"
              type="button"
              onClick={() => window.location.reload()}
            >
              {this.props.text('refresh')}
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
