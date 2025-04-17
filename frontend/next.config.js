/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath: "/next",
  compiler: {
    emotion: true,
  },
  // output: "export",
  reactStrictMode: true,
};

module.exports = nextConfig;
