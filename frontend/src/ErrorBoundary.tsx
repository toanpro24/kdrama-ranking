import { Component } from "react";
import type { ReactNode, ErrorInfo } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <span className="error-boundary-icon">!</span>
          <h2 className="error-boundary-title">Something went wrong</h2>
          <p className="error-boundary-msg">{this.state.error?.message || "An unexpected error occurred."}</p>
          <button
            className="error-boundary-btn"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.href = "/";
            }}
          >
            Return Home
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
