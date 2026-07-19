import { NextRequest } from "next/server";

const ALLOWED_HOSTNAME = "images.pokemontcg.io";

export async function GET(request: NextRequest): Promise<Response> {
  const rawUrl = request.nextUrl.searchParams.get("url");

  if (!rawUrl) {
    return new Response("Missing url parameter", { status: 400 });
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(rawUrl);
  } catch {
    return new Response("Invalid url parameter", { status: 400 });
  }

  if (parsedUrl.hostname !== ALLOWED_HOSTNAME) {
    return new Response("Hostname not allowed", { status: 400 });
  }

  const upstreamResponse = await fetch(parsedUrl.toString());

  if (!upstreamResponse.ok) {
    return new Response("Failed to fetch upstream image", {
      status: upstreamResponse.status,
    });
  }

  const imageArrayBuffer = await upstreamResponse.arrayBuffer();
  const contentType = upstreamResponse.headers.get("content-type") ?? "image/png";

  return new Response(imageArrayBuffer, {
    headers: {
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=86400",
    },
  });
}
