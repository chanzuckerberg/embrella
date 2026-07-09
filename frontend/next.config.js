/** @type {import('next').NextConfig} */
const nextConfig = {
  compiler: {
    emotion: true,
  },
  transpilePackages: ['@czi-sds/components', '@czi-sds/data-viz'],
  allowedDevOrigins: ['nginx', 'frontend'],
  async redirects() {
    // Feature-section bare paths have no screen of their own — forward each to its default sub-route 
    return [
      { source: '/samples', destination: '/samples/grids', permanent: false },
      { source: '/sessions', destination: '/sessions/browse', permanent: false },
      { source: '/processing', destination: '/processing/jobs/monitor', permanent: false },
      { source: '/deposition', destination: '/deposition/submissions', permanent: false },
    ];
  },
};

module.exports = nextConfig;
