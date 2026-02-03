import { Injectable, signal, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

declare const google: any;

export interface GoogleUser {
    id: string;
    email: string;
    name: string;
    picture: string;
    given_name?: string;
    family_name?: string;
}

/**
 * Auth Service - Handles Google One Tap Sign-In using Google Identity Services.
 * 
 * SETUP INSTRUCTIONS:
 * 
 * 1. Go to Google Cloud Console:
 *    https://console.cloud.google.com/apis/credentials
 * 
 * 2. Create an OAuth 2.0 Client ID:
 *    - Click "Create Credentials" > "OAuth client ID"
 *    - Select "Web application"
 *    - Name: "Genkit Chat"
 * 
 * 3. Configure authorized origins:
 *    - Add: http://localhost:4200
 *    - Add: http://localhost:49230
 *    - Add your production domain
 * 
 * 4. Copy the Client ID and set it:
 *    - Option A: Set GOOGLE_OAUTH_CLIENT_ID environment variable
 *    - Option B: Replace CLIENT_ID constant below
 * 
 * 5. Ensure OAuth consent screen is configured:
 *    - Publishing status: Testing (or Production)
 *    - Add test users if in Testing mode
 * 
 * Future: This will be extended to support Google Drive API for file attachments.
 */
@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private platformId = inject(PLATFORM_ID);

    // Set your Google OAuth Client ID here
    // Get one from: https://console.cloud.google.com/apis/credentials
    private readonly CLIENT_ID =
        (typeof window !== 'undefined' && (window as any).__GOOGLE_OAUTH_CLIENT_ID__) ||
        // Replace the empty string below with your Client ID:
        '';

    user = signal<GoogleUser | null>(null);
    isInitialized = signal(false);
    isLoading = signal(false);
    demoMode = signal(false);

    // Demo user for testing UI
    private readonly DEMO_USER: GoogleUser = {
        id: 'demo-user-123',
        email: 'avyanna@genkit.dev',
        name: 'Avyanna',
        picture: 'https://lh3.googleusercontent.com/a/default-user=s96-c',
        given_name: 'Avyanna',
    };

    constructor() {
        if (isPlatformBrowser(this.platformId)) {
            this.restoreDemoMode();
            this.restoreSession();
            this.initGoogleSignIn();
        }
    }

    /**
     * Toggle demo mode on/off.
     * When enabled, simulates a signed-in user session.
     */
    toggleDemoMode(): void {
        const newValue = !this.demoMode();
        this.demoMode.set(newValue);
        localStorage.setItem('gauth_demo_mode', String(newValue));

        if (newValue) {
            // Enable demo mode - sign in as demo user
            this.user.set(this.DEMO_USER);
            localStorage.setItem('gauth_user', JSON.stringify(this.DEMO_USER));
        } else {
            // Disable demo mode - sign out
            this.user.set(null);
            localStorage.removeItem('gauth_user');
            localStorage.removeItem('gauth_token');
        }
    }

    private restoreDemoMode(): void {
        const stored = localStorage.getItem('gauth_demo_mode');
        if (stored === 'true') {
            this.demoMode.set(true);
        }
    }

    private initGoogleSignIn(): void {
        // Wait for Google Identity Services to load
        const checkGoogle = setInterval(() => {
            if (typeof google !== 'undefined' && google.accounts) {
                clearInterval(checkGoogle);
                this.setupGoogleSignIn();
            }
        }, 100);

        // Timeout after 5 seconds
        setTimeout(() => {
            clearInterval(checkGoogle);
            if (!this.isInitialized()) {
                console.log('Google Identity Services did not load. Check if the GSI script is included in index.html');
                this.isInitialized.set(true);
            }
        }, 5000);
    }

    private setupGoogleSignIn(): void {
        if (!this.CLIENT_ID) {
            console.log(`
╔══════════════════════════════════════════════════════════════════════════╗
║  Google Sign-In: Demo User                                                ║
╠══════════════════════════════════════════════════════════════════════════╣
║  No CLIENT_ID configured. Using demo user for testing.                    ║
║                                                                           ║
║  To enable real Google Sign-In:                                           ║
║  1. Create OAuth Client ID at:                                            ║
║     https://console.cloud.google.com/apis/credentials                     ║
║  2. Add localhost origins (4200, 49230)                                   ║
║  3. Set CLIENT_ID in auth.service.ts                                      ║
╚══════════════════════════════════════════════════════════════════════════╝
            `);
            this.isInitialized.set(true);
            return;
        }

        try {
            google.accounts.id.initialize({
                client_id: this.CLIENT_ID,
                callback: (response: any) => this.handleCredentialResponse(response),
                auto_select: true,        // Auto sign-in if one account
                cancel_on_tap_outside: true,
                itp_support: true,        // Support for Intelligent Tracking Prevention
                prompt_parent_id: 'g_id_onload', // Parent element ID
                context: 'signin',
            });

            this.isInitialized.set(true);
            console.log('Google Sign-In initialized successfully');

            // Show One Tap prompt if user is not signed in
            if (!this.user()) {
                this.showOneTap();
            }
        } catch (error) {
            console.error('Failed to initialize Google Sign-In:', error);
            this.isInitialized.set(true);
        }
    }

    private showOneTap(): void {
        if (!this.CLIENT_ID || typeof google === 'undefined') return;

        google.accounts.id.prompt((notification: any) => {
            if (notification.isDisplayed()) {
                console.log('One Tap prompt displayed');
            } else if (notification.isNotDisplayed()) {
                console.log('One Tap not displayed:', notification.getNotDisplayedReason());
            } else if (notification.isSkippedMoment()) {
                console.log('One Tap skipped:', notification.getSkippedReason());
            } else if (notification.isDismissedMoment()) {
                console.log('One Tap dismissed:', notification.getDismissedReason());
            }
        });
    }

    private handleCredentialResponse(response: any): void {
        if (response.credential) {
            // Decode the JWT token to get user info
            const payload = this.decodeJwt(response.credential);

            const user: GoogleUser = {
                id: payload.sub,
                email: payload.email,
                name: payload.name,
                picture: payload.picture,
                given_name: payload.given_name,
                family_name: payload.family_name,
            };

            this.user.set(user);

            // Store in localStorage for persistence
            localStorage.setItem('gauth_user', JSON.stringify(user));
            localStorage.setItem('gauth_token', response.credential);

            console.log('User signed in:', payload.email);
        }
        this.isLoading.set(false);
    }

    private decodeJwt(token: string): any {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            atob(base64)
                .split('')
                .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(jsonPayload);
    }

    /**
     * Initiate sign-in flow.
     * Shows One Tap if CLIENT_ID is configured, otherwise uses demo mode.
     */
    signIn(): void {
        if (!this.CLIENT_ID) {
            // Demo mode - show a mock user
            this.user.set({
                id: 'demo-user',
                email: 'demo@genkit.dev',
                name: 'Demo User',
                picture: '',
                given_name: 'Demo',
            });
            localStorage.setItem('gauth_user', JSON.stringify(this.user()));
            return;
        }

        if (typeof google !== 'undefined' && google.accounts) {
            this.isLoading.set(true);
            google.accounts.id.prompt((notification: any) => {
                if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                    // One Tap was blocked (e.g., by browser settings)
                    this.isLoading.set(false);
                    console.log('One Tap blocked. Consider adding a fallback sign-in button.');
                }
            });
        }
    }

    /**
     * Sign out the current user.
     */
    signOut(): void {
        if (typeof google !== 'undefined' && google.accounts && this.CLIENT_ID) {
            google.accounts.id.disableAutoSelect();
            // Revoke the token
            const token = localStorage.getItem('gauth_token');
            if (token) {
                google.accounts.id.revoke(this.user()?.email || '', () => {
                    console.log('Token revoked');
                });
            }
        }

        this.user.set(null);
        localStorage.removeItem('gauth_user');
        localStorage.removeItem('gauth_token');
        console.log('User signed out');
    }

    /**
     * Restore session from localStorage.
     */
    restoreSession(): void {
        const stored = localStorage.getItem('gauth_user');
        if (stored) {
            try {
                const user = JSON.parse(stored);
                this.user.set(user);
                console.log('Session restored for:', user.email);
            } catch {
                localStorage.removeItem('gauth_user');
                localStorage.removeItem('gauth_token');
            }
        }
    }

    /**
     * Check if user is signed in.
     */
    isSignedIn(): boolean {
        return this.user() !== null;
    }

    /**
     * Get initials for avatar display.
     */
    getInitials(): string {
        const u = this.user();
        if (!u) return '?';
        if (u.given_name && u.family_name) {
            return (u.given_name[0] + u.family_name[0]).toUpperCase();
        }
        return u.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || '?';
    }

    /**
     * Get the stored OAuth token (for API calls).
     */
    getToken(): string | null {
        return localStorage.getItem('gauth_token');
    }

    /**
     * Update the user's display name.
     */
    updateName(givenName: string): void {
        const currentUser = this.user();
        if (currentUser) {
            const updatedUser = {
                ...currentUser,
                given_name: givenName,
                name: givenName + (currentUser.family_name ? ' ' + currentUser.family_name : ''),
            };
            this.user.set(updatedUser);
            localStorage.setItem('gauth_user', JSON.stringify(updatedUser));
        }
    }
}
