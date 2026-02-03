import type { StorybookConfig } from '@storybook/angular';

const config: StorybookConfig = {
  stories: [
    '../src/**/*.mdx',
    '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'
  ],
  addons: [
    '@storybook/addon-a11y',
    '@storybook/addon-docs',
    '@storybook/addon-onboarding'
  ],
  framework: '@storybook/angular',
  core: {
    disableTelemetry: true,
  },
  staticDirs: [
    { from: '../src/assets', to: '/assets' },
    { from: '../public', to: '/' },
  ],
  styles: ['../src/styles.scss'],
};
export default config;