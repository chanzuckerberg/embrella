// Lazy stand-in for the `@mui/icons-material` barrel: SDS's CJS bundle requires it,
// loading ~11k icon files (~15s) per test file. Loads only icons accessed instead.
module.exports = new Proxy(
  {},
  {
    get(cache, name) {
      if (name === '__esModule') return true;
      if (typeof name !== 'string') return undefined;
      if (name in cache) return cache[name];

      try {
        // Sync lazy load per icon; `import` can't do this.
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        cache[name] = require(`@mui/icons-material/${name}`).default;
      } catch {
        cache[name] = undefined;
      }
      return cache[name];
    },
  }
);
