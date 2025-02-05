# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.05"; # or "unstable"
  # Use https://search.nixos.org/packages to find packages
  packages = [
    pkgs.nodejs_20
    pkgs.util-linux
    # pkgs.go
  ];
  # Sets environment variables in the workspace
  env = {
    #TODO Get a API key from https://g.co/ai/idxGetGeminiKey 
    GOOGLE_GENAI_API_KEY = ""; 
  };
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      # "vscodevim.vim"
      # "golang.go"
    ];

    # Workspace lifecycle hooks
    workspace = {
      # Runs when a workspace is first created
      onCreate = {
        npm-install = "npm ci --no-audit --prefer-offline --no-progress --timing";
        default.openFiles = [ "README.md" "index.ts" ];
      };
      # Runs when the workspace is (re)started
      onStart = {
        run-server = "if [ -z \"\${GOOGLE_GENAI_API_KEY}\" ]; then \
          echo 'No Gemini API key detected, enter a Gemini API key from https://aistudio.google.com/app/apikey:' && \
          read -s GOOGLE_GENAI_API_KEY && \
          echo 'You can also add to .idx/dev.nix to automatically add to your workspace'
          export GOOGLE_GENAI_API_KEY; \
          fi && \
          npm run genkit:dev";
      };
    };
  };
}