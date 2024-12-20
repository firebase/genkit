/** @type {import('ts-jest').JestConfigWithTsJest} **/
export default {
  verbose: true,
  testEnvironment: 'node',
  transform: {
    '^.+.tsx?$': ['ts-jest', {}],
  },
};
