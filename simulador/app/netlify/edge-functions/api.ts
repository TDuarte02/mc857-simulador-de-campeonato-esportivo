// Forwards /api/* to the API Gateway and adds the x-api-key header. The page and
// the API then share the same origin, so the browser needs no CORS, and the key
// stays on Netlify instead of in the web bundle.
//
// Environment variables of the Netlify site:
//   API_KEY       required, the API Gateway key
//   API_BASE_URL  optional, defaults to the AWS address below

declare const Netlify: { env: { get(name: string): string | undefined } };

const DEFAULT_BASE_URL = "https://6cpiwkgj2d.execute-api.us-east-2.amazonaws.com/v1";

// Hop-by-hop and Netlify headers that must not be forwarded to the API.
// accept-encoding goes too: fetch decompresses the body, so ask for it plain.
const DROPPED_REQUEST_HEADERS = [
    "host", "connection", "cookie", "accept-encoding", "x-forwarded-for", "x-forwarded-host", "x-nf-request-id",
];
// The body handed back is already decoded, so its original size and encoding no longer apply.
const DROPPED_RESPONSE_HEADERS = ["connection", "content-encoding", "content-length", "transfer-encoding"];

function error(status: number, code: string, message: string): Response {
    return Response.json({ error: { code, message } }, { status });
}

export default async (request: Request): Promise<Response> => {
    const apiKey = Netlify.env.get("API_KEY");
    if (!apiKey) return error(500, "PROXY_MISCONFIGURED", "API_KEY is not set on the Netlify site.");

    const baseUrl = (Netlify.env.get("API_BASE_URL") ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    const url = new URL(request.url);
    const target = baseUrl + url.pathname.replace(/^\/api/, "") + url.search;

    const headers = new Headers(request.headers);
    for (const name of DROPPED_REQUEST_HEADERS) headers.delete(name);
    headers.set("x-api-key", apiKey);

    const hasBody = request.method !== "GET" && request.method !== "HEAD";
    try {
        const response = await fetch(target, {
            method: request.method,
            headers,
            body: hasBody ? await request.arrayBuffer() : undefined,
        });
        const responseHeaders = new Headers(response.headers);
        for (const name of DROPPED_RESPONSE_HEADERS) responseHeaders.delete(name);
        return new Response(response.body, { status: response.status, headers: responseHeaders });
    } catch {
        return error(502, "UPSTREAM_UNREACHABLE", "Could not reach the API.");
    }
};

export const config = { path: "/api/*" };
