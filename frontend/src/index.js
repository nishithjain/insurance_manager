import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// Chrome quirk: ResizeObserver can fire during layout; CRA overlay treats it as fatal. Harmless.
function isBenignResizeObserverError(msg) {
  return (
    typeof msg === "string" &&
    msg.includes("ResizeObserver loop") &&
    msg.includes("undelivered notifications")
  );
}
window.addEventListener(
  "error",
  (e) => {
    if (isBenignResizeObserverError(e?.message)) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
    }
  },
  true
);

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
