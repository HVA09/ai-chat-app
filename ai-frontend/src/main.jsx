import React from "react";
import ReactDOM from "react-dom/client";
import SidebarActionsPreview from "./SidebarActionsPreview";
import ErrorBoundary from "./components/ErrorBoundary";
import "./index.css";
import "./i18n";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <SidebarActionsPreview />
    </ErrorBoundary>
  </React.StrictMode>
);
