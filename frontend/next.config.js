/** @type {import('next').NextConfig} */
const nextConfig = {
  compiler: {
    emotion: true,
  },
  transpilePackages: ['@czi-sds/components', '@czi-sds/data-viz'],
  // The dev server only trusts localhost origins by default; in the devcontainer
  // it's reached via the `nginx` / `frontend` service hostnames (e.g. Playwright
  // E2E), so the HMR/dev runtime is blocked and the app never hydrates. Allow them.
  allowedDevOrigins: ['nginx', 'frontend'],
};

module.exports = nextConfig;
