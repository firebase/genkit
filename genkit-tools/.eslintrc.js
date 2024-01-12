module.exports = {
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
    rules: {
      "jsdoc/newline-after-description": "off",
      "new-cap": "off",  // Function components in Angular use this
      "jsdoc/require-jsdoc": ["warn", { publicOnly: true }],
      "no-restricted-globals": ["error", "name", "length"],
      "prefer-arrow-callback": "error",
      "prettier/prettier": ["error", { singleQuote: true, tabWidth: 2 }],
      "require-atomic-updates": "off", // This rule is so noisy and isn't useful: https://github.com/eslint/eslint/issues/11899
      "require-jsdoc": "off", // This rule is deprecated and superseded by jsdoc/require-jsdoc.
      "valid-jsdoc": "off", // This is deprecated but included in recommended configs.
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
          "no-invalid-this": "off", // Turned off in favor of @typescript-eslint/no-invalid-this.
          "no-unused-vars": "off", // Off in favor of @typescript-eslint/no-unused-vars.
          eqeqeq: ["error", "always", { null: "ignore" }],
          camelcase: ["error", { properties: "never" }], // snake_case allowed in properties iif to satisfy an external contract / style
  
          "@typescript-eslint/explicit-function-return-type": ["error", { allowExpressions: true }], 
          "@typescript-eslint/no-use-before-define": ["error", { functions: false, typedefs: false }],
          "@typescript-eslint/prefer-includes": "error",
        },
      },
    ],
    globals: {},
    parserOptions: {
      ecmaVersion: "2017",
      project: ["tsconfig.json", "ui/tsconfig.json"],
      sourceType: "module",
      warnOnUnsupportedTypeScriptVersion: false,
    },
    plugins: ["prettier", "@typescript-eslint", "jsdoc"],
    settings: {
      jsdoc: {
        tagNamePreference: {
          returns: "return",
        },
      },
    },
    parser: "@typescript-eslint/parser",
  };