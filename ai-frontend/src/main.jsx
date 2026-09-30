import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AppDialogProvider } from "./components/AppDialog";
import ErrorBoundary from "./components/ErrorBoundary";
import "./index.css";
import "./i18n";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AppDialogProvider>
        <App />
      </AppDialogProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
