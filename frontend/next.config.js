/** @type {import('next').NextConfig} */
const nextConfig = {
  compiler: {
    emotion: {
      autoLabel: 'never',
      sourceMap: false,
    },
  },
  // output: "export",
  reactStrictMode: true,
};

module.exports = nextConfig;
