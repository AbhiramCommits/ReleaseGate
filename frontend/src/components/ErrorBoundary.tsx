import { Component, ErrorInfo, ReactNode } from "react";
import styles from "./ErrorBoundary.module.css";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Unhandled render error", error, info);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className={styles.fallback} role="alert">
          <h1 className={styles.title}>Something went wrong</h1>
          <p className={styles.message}>{this.state.error.message}</p>
          <button
            className={styles.retry}
            type="button"
            onClick={() => this.setState({ error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
