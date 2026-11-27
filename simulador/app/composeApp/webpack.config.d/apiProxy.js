// Local stand-in for the Netlify edge function (netlify/edge-functions/api.ts):
// the dev server (./gradlew wasmJsBrowserDevelopmentRun) forwards /api/* to the
// API Gateway and adds the x-api-key header, so the browser stays on localhost
// and needs no CORS. Reads api.baseUrl and api.key from simulador/app/local.properties.
;(function () {
    const fs = require("fs");
    const path = require("path");

    const DEFAULT_BASE_URL = "https://6cpiwkgj2d.execute-api.us-east-2.amazonaws.com/v1";

    // Webpack runs inside build/js/packages/composeApp: look upwards for local.properties.
    function readLocalProperties() {
        let dir = process.cwd();
        while (true) {
            const file = path.join(dir, "local.properties");
            if (fs.existsSync(file)) {
                const props = {};
                for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
                    const match = line.match(/^\s*([^#!=\s][^=]*?)\s*=\s*(.*?)\s*$/);
                    if (match) props[match[1]] = match[2];
                }
                return props;
            }
            const parent = path.dirname(dir);
            if (parent === dir) return {};
            dir = parent;
        }
    }

    const props = readLocalProperties();
    const baseUrl = (props["api.baseUrl"] || DEFAULT_BASE_URL).replace(/\/+$/, "");
    const apiKey = props["api.key"] || "";
    if (!apiKey) console.warn("api.key is not set in local.properties; the API will answer 403.");

    config.devServer = config.devServer || {};
    config.devServer.proxy = [].concat(config.devServer.proxy || [], [{
        context: ["/api"],
        target: baseUrl,
        changeOrigin: true,
        pathRewrite: { "^/api": "" },
        headers: apiKey ? { "x-api-key": apiKey } : {},
    }]);
})();
