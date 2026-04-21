import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    },
  },
  // EPS single-consumer rule — see docs/eps-port-spec.md §4.0.1.
  // useEps() must only be called from EpsPage.tsx (the canonical
  // consumer) or EpsProvider.tsx (which declares it). Pushing it
  // into child components defeats React.memo and turns every packet
  // into a whole-tree rerender.
  {
    files: ['src/plugins/maveric/eps/**/*.{ts,tsx}'],
    ignores: [
      'src/plugins/maveric/eps/EpsPage.tsx',
      'src/plugins/maveric/eps/EpsProvider.tsx',
    ],
    rules: {
      'no-restricted-imports': ['error', {
        patterns: [{
          group: ['**/EpsProvider'],
          importNames: ['useEps'],
          message:
            'useEps() may only be called from EpsPage.tsx. Move the state read to the page and pass narrow props down. See docs/eps-port-spec.md §4.0.1.',
        }],
      }],
    },
  },
])
