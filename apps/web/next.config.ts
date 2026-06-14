import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // GAPS.md P4-7 — ``output: "standalone"`` produceert een
  // ``.next/standalone`` directory met enkel de runtime-bestanden
  // die ``node server.js`` nodig heeft (een gesnoeide subset van
  // ``node_modules``). De Dockerfile kopieert daaruit i.p.v. de
  // volledige ``node_modules`` mee te slepen — scheelt ~300 MB in
  // het productie-image.
  output: "standalone",
};

export default nextConfig;
