/**
 * CRA dev server: proxy /api to local FastAPI so REACT_APP_BACKEND_URL can be empty.
 * https://create-react-app.dev/docs/proxying-api-requests-in-development/
 */
const { createProxyMiddleware } = require("http-proxy-middleware");

module.exports = function proxy(app) {
  const target = process.env.REACT_APP_PROXY_TARGET || "http://127.0.0.1:8000";
  app.use(
    "/api",
    createProxyMiddleware({
      target,
      changeOrigin: true,
    })
  );
};
