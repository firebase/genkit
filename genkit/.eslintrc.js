module.exports = {
  root: true,
  env: {
    es6: true,
    node: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:@typescript-eslint/recommended-requiring-type-checking",
    "plugin:jsdoc/recommended",
    "google",
    "prettier",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    project: ["tsconfig.json", "tsconfig.dev.json"],
    sourceType: "module",
  },
  ignorePatterns: [
    "**/lib/**/*", // Ignore built files.
    "**/node_modules/**", // Ignore built files.
  ],
  plugins: ["prettier", "@typescript-eslint", "jsdoc"],
  rules: {
    "jsdoc/newline-after-description": "off",
    "jsdoc/require-jsdoc": ["warn", { publicOnly: true }],
    "no-restricted-globals": ["error", "name", "length"],
    "prefer-arrow-callback": "error",
    "prettier/prettier": "error",
    "require-atomic-updates": "off", // This rule is so noisy and isn't useful: https://github.com/eslint/eslint/issues/11899
    "require-jsdoc": "off", // This rule is deprecated and superseded by jsdoc/require-jsdoc.
    "valid-jsdoc": "off", // This is deprecated but included in recommended configs.

    "no-prototype-builtins": "warn",
    "no-useless-escape": "warn",
    "prefer-promise-reject-errors": "warn",

    "quotes": ["error", "single", { "avoidEscape": true }],
    "import/no-unresolved": 0,
    "import/no-named-as-default": 0,
    "indent": ["error", 2],
    "max-len": ["error", { "code": 100, "ignoreComments": true }]
  },
  overrides: [
    {
      files: ["*.ts"],
      rules: {
        "jsdoc/require-param-type": "off",
        "jsdoc/require-returns-type": "off",

        // Google style guide allows us to omit trivial parameters and returns
        "jsdoc/require-param": "off",
        "jsdoc/require-returns": "off",

        "@typescript-eslint/no-invalid-this": "error",
        "@typescript-eslint/no-unused-vars": "error", // Unused vars should not exist.
        "@typescript-eslint/no-misused-promises": "warn", // rule does not work with async handlers for express.
        "no-invalid-this": "off", // Turned off in favor of @typescript-eslint/no-invalid-this.
        "no-unused-vars": "off", // Off in favor of @typescript-eslint/no-unused-vars.
        eqeqeq: ["error", "always", { null: "ignore" }],
        camelcase: ["error", { properties: "never" }], // snake_case allowed in properties iif to satisfy an external contract / style

        // Ideally, all these warning should be error - let's fix them in  the future.
        "@typescript-eslint/no-unsafe-argument": "warn",
        "@typescript-eslint/no-unsafe-assignment": "warn",
        "@typescript-eslint/no-unsafe-call": "warn",
        "@typescript-eslint/no-unsafe-member-access": "warn",
        "@typescript-eslint/no-unsafe-return": "warn",
        "@typescript-eslint/restrict-template-expressions": "warn",
        "@typescript-eslint/require-await": "warn",
      },
    },
  ]
};
