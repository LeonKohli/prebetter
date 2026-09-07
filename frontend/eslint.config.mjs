import withNuxt from './.nuxt/eslint.config.mjs'
import unicorn from 'eslint-plugin-unicorn'

export default withNuxt({
  files: ['**/*.{ts,tsx,mts,cts,vue}'],
  linterOptions: { reportUnusedDisableDirectives: 'error' },
  plugins: { unicorn },
  rules: {
    eqeqeq: ['error', 'always', { null: 'ignore' }],
    'no-constant-binary-expression': 'error',
    'no-else-return': 'error',
    'preserve-caught-error': 'error',
    'max-statements': ['warn', 40],
    '@typescript-eslint/no-shadow': 'error',
    '@typescript-eslint/no-unnecessary-boolean-literal-compare': 'error',
    '@typescript-eslint/prefer-optional-chain': 'error',
    '@typescript-eslint/require-array-sort-compare': 'error',
    '@typescript-eslint/switch-exhaustiveness-check': 'error',
    '@typescript-eslint/no-deprecated': 'warn',
    '@typescript-eslint/no-unnecessary-condition': 'warn',
    '@typescript-eslint/prefer-nullish-coalescing': 'warn',
    'unicorn/consistent-function-scoping': 'warn',
    'vue/multi-word-component-names': 'warn',
  },
})
