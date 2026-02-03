import type { Preview } from '@storybook/angular';
import { setCompodocJson } from '@storybook/addon-docs/angular';

// Apply global styles for Storybook
import '../src/theme/styles.css';

const preview: Preview = {
    parameters: {
        controls: {
            matchers: {
                color: /(background|color)$/i,
                date: /Date$/i,
            },
        },
        backgrounds: {
            options: {
                light: { name: 'light', value: '#fafafa' },
                dark: { name: 'dark', value: '#1a1c1e' }
            }
        },
    },

    decorators: [],

    initialGlobals: {
        backgrounds: {
            value: 'light'
        }
    }
};

export default preview;
