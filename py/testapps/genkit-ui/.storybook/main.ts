import type { StorybookConfig } from '@storybook/angular';

const config: StorybookConfig = {
    stories: ['../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'],
    addons: ['@storybook/addon-docs', '@storybook/addon-a11y'],

    framework: {
        name: '@storybook/angular',
        options: {
            enableIvy: true,
        },
    },

    core: {
        disableTelemetry: true,
    },
};

export default config;
