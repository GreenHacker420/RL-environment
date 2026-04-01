const OPENENV_API_BASE = process.env.OPENENV_API_BASE ?? "http://127.0.0.1:8000";

type Params = { path: string[] };

async function proxy(request: Request, params: Promise<Params>) {
  const { path } = await params;
  const upstreamUrl = new URL(`${OPENENV_API_BASE}/${path.join("/")}`);
  const searchParams = new URL(request.url).searchParams;
  searchParams.forEach((value, key) => {
    upstreamUrl.searchParams.set(key, value);
  });

  const contentType = request.headers.get("content-type");
  const bodyText =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.text();

  const response = await fetch(upstreamUrl, {
    method: request.method,
    headers: contentType ? { "content-type": contentType } : undefined,
    body: bodyText,
    cache: "no-store",
  });

  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function GET(
  request: Request,
  context: { params: Promise<Params> },
) {
  return proxy(request, context.params);
}
