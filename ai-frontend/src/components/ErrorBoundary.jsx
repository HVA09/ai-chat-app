import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: "", componentStack: "" };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error instanceof Error ? error.message : String(error),
    };
  }

  componentDidCatch(error, info) {
    console.error("خطأ غير متوقع بالواجهة:", error, info);
    this.setState({
      errorMessage: error instanceof Error ? error.message : String(error),
      componentStack: info?.componentStack || "",
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-3 bg-slate-50 p-6 text-center">
          <h2 className="text-lg font-semibold text-slate-900">حدث خطأ غير متوقع</h2>
          <p className="max-w-sm text-sm text-slate-500">
            صار في مشكلة في عرض الصفحة. جرّب تحديث الصفحة، ولو استمرت المشكلة راجع الكونسول.
          </p>
          {new URLSearchParams(window.location.search).get("debug") === "1" ? (
            <pre className="max-h-64 w-full max-w-2xl overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-100 p-3 text-left text-xs text-red-800">
              {this.state.errorMessage}
              {"\n"}
              {this.state.componentStack}
            </pre>
          ) : null}
          <button
            onClick={() => window.location.reload()}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1"
          >
            تحديث الصفحة
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
