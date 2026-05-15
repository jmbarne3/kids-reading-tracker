const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const projectRoot = __dirname;
const monorepoRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);

// Tell Metro to watch the entire monorepo so cross-package imports work.
config.watchFolders = [monorepoRoot];

// Resolve modules from the app first, then fall back to the monorepo root.
// This ensures the app's pinned dependency versions take precedence.
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(monorepoRoot, 'node_modules'),
];

// Force all 'react' imports — including subpath imports like 'react/jsx-runtime'
// and 'react/jsx-dev-runtime' used by the JSX transform — to always resolve
// from the app's own node_modules.  extraNodeModules only matches exact names
// so it misses those subpaths; resolveRequest intercepts everything.
// Without this, npm workspaces hoists react@19.2.6 (from the Vite apps) to the
// root node_modules while the mobile app needs 19.1.0, and Metro ends up
// loading two React instances → "invalid hook call" at runtime.
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (moduleName === 'react' || moduleName.startsWith('react/')) {
    return {
      filePath: require.resolve(moduleName, { paths: [projectRoot] }),
      type: 'sourceFile',
    };
  }
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
