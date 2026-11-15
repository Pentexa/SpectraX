const mirrors = [
  "https://stpubdata.s3.us-east-1.amazonaws.com/mast/skybackgrounds/DSSColor",
  "https://irsa.ipac.caltech.edu/data/hips/CDS/DSS2/color",
];

function isDssTile(path: string) {
  if (path === "Norder3/Allsky.jpg") return true;
  const parts = /^Norder([0-9])\/Dir(\d{1,7})\/Npix(\d{1,7})\.jpg$/.exec(path);
  if (!parts) return false;
  const [, order, directory, pixel] = parts.map(Number);
  return pixel < 12 * 4 ** order && directory === Math.floor(pixel / 10_000) * 10_000
    && path === `Norder${order}/Dir${directory}/Npix${pixel}.jpg`;
}

export async function GET(_: Request, { params }: { params: Promise<{ tile: string[] }> }) {
  const path = (await params).tile.join("/");
  if (!isDssTile(path)) return new Response(null, { status: 404 });

  for (const mirror of mirrors) {
    try {
      const response = await fetch(`${mirror}/${path}`, {
        redirect: "error",
        signal: AbortSignal.timeout(6_000),
        next: { revalidate: 86_400 },
      });
      if (!response.ok) continue;
      const bytes = new Uint8Array(await response.arrayBuffer());
      if (bytes[0] !== 0xff || bytes[1] !== 0xd8 || bytes[2] !== 0xff) continue;
      return new Response(bytes, {
        headers: {
          "Content-Type": "image/jpeg",
          "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
        },
      });
    } catch {
      // Try the other DSS2 mirror when this request times out or disconnects.
    }
  }
  return new Response(null, { status: 503, headers: { "Retry-After": "5" } });
}
