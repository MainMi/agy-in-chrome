export default [
  {
    ignores: ["**/node_modules/**", "**/dist/**", "**/build/**", "**/.venv/**", "**/vendor/**"]
  },
  {
    rules: {
      "max-lines": ["error", { max: 250, skipBlankLines: true, skipComments: true }],
      "max-lines-per-function": ["warn", { max: 50, skipBlankLines: true, skipComments: true }]
    }
  }
];
