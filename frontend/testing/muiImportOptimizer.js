// Lazy stand-ins for MUI barrels: load only the exports a test touches instead of
// every file the barrel re-exports. Wired up in jest.setup.js.
//   icons-material  SDS's CJS bundle requires it: ~11k files (~15s) per test file
//   material        ~2s per test file
/* eslint-disable @typescript-eslint/no-require-imports */
/* global jest */
// Sync lazy loads; `import` can't do this.

const CLASSES_SUFFIX = 'Classes';

// Proxy that resolves each export once via `load`; unresolvable names cache as undefined
function lazyBarrel(load) {
  return new Proxy(
    {},
    {
      get(cache, name) {
        if (name === '__esModule') return true;
        if (typeof name !== 'string') return undefined;
        if (!(name in cache)) cache[name] = load(name);
        return cache[name];
      },
    }
  );
}

function tryRequire(path) {
  try {
    return require(path);
  } catch {
    return undefined;
  }
}

// e.g. AddPhotoAlternate → @mui/icons-material/AddPhotoAlternate
const iconsMaterial = lazyBarrel((name) => tryRequire(`@mui/icons-material/${name}`)?.default);

// Box → @mui/material/Box
function materialSubpath(name) {
  const mod = tryRequire(`@mui/material/${name}`);
  return mod && 'default' in mod ? mod.default : mod;
}

// autocompleteClasses → @mui/material/Autocomplete
function materialClasses(name) {
  if (!name.endsWith(CLASSES_SUFFIX)) return undefined;

  const component = name[0].toUpperCase() + name.slice(1, -CLASSES_SUFFIX.length);
  return tryRequire(`@mui/material/${component}`)?.[name];
}

// Falls back to the styles module (alpha, createTheme), then the real barrel (slow, rare)
const material = lazyBarrel(
  (name) =>
    materialSubpath(name) ??
    materialClasses(name) ??
    require('@mui/material/styles')[name] ??
    jest.requireActual('@mui/material')[name]
);

module.exports = { iconsMaterial, material };
