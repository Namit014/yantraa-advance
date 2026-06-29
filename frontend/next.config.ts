import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  productionBrowserSourceMaps: false,
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
