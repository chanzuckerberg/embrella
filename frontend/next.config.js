/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath: "/next",
  compiler: {
    emotion: true,
  },
  output: "export",
};

module.exports = nextConfig;
