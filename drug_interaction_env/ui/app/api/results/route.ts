import { readFile } from "node:fs/promises";
import path from "node:path";

export async function GET() {
  const resultsPath = path.resolve(process.cwd(), "..", "results.json");

  try {
    const raw = await readFile(resultsPath, "utf8");
    return new Response(raw, {
      headers: {
        "content-type": "application/json",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "results.json could not be read";

    return Response.json(
      { error: `No benchmark results available yet: ${message}` },
      { status: 404 },
    );
  }
}
