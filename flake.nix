# flake.nix
{
  description = "Development environment for the Genkit project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # --- Pin versions based on bin/setup ---
        nodeVersion = 23;
        pnpmVersion = "10.2.0";
        # golangciLintVersion = "2.0.2"; # Check nixpkgs for exact version availability

        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true; # Needed for google-cloud-sdk sometimes
          };
        };

        # --- Python Environment ---
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          httpie
          mypy
          ruff
          mkdocs
          mkdocs-material
          mkdocs-autorefs
          #mkdocs-literate-nav # Needs investigation why it's not found
          mkdocs-minify-plugin
          mkdocs-mermaid2-plugin
          # mkdocs-d2-plugin # Requires d2 executable, provided separately below
          mkdocstrings # Requires mkdocstrings-python for python support
          mkdocstrings-python
        ]);

        # --- Go Tools ---
        # Check nixpkgs for availability and exact names for commented items
        goTools = with pkgs; [
          go
          gotools
          go-licenses
          govulncheck
          lazygit
          addlicense
          golangci-lint
          # Captainhook (Example - needs buildGoModule)
          # (buildGoModule {
          #   pname = "captainhook";
          #   version = "latest"; # Specify a real version/tag
          #   src = fetchFromGitHub {
          #     owner = "captainhook-go";
          #     repo = "captainhook";
          #     rev = "main"; # Specify a real version/tag
          #     sha256 = lib.fakeSha256; # Replace with actual hash
          #   };
          #   vendorHash = null;
          # })
          # go-global-update (Example - needs buildGoModule)
          # (buildGoModule {
          #   pname = "go-global-update";
          #   version = "latest"; # Specify a real version/tag
          #   src = fetchFromGitHub {
          #     owner = "Gelio";
          #     repo = "go-global-update";
          #     rev = "main"; # Specify a real version/tag
          #     sha256 = lib.fakeSha256; # Replace with actual hash
          #   };
          #   vendorHash = null;
          # })
        ];

        # --- Rust Tools ---
        # Check nixpkgs for availability for commented items
        rustTools = with pkgs; [
          rustup
          convco
          taplo-cli
          # pylyzer (Example - needs buildRustPackage)
          # (rustPlatform.buildRustPackage {
          #   pname = "pylyzer";
          #   version = "latest"; # Specify a real version/tag
          #   src = fetchFromGitHub {
          #     owner = "pylyzer";
          #     repo = "pylyzer";
          #     rev = "main"; # Specify a real version/tag
          #     sha256 = lib.fakeSha256;
          #   };
          #   cargoSha256 = lib.fakeSha256;
          # })
          # rust-parallel (Example - needs buildRustPackage)
          # (rustPlatform.buildRustPackage {
          #   pname = "rust-parallel";
          #   version = "latest"; # Specify a real version/tag
          #   src = fetchFromGitHub {
          #     owner = "termoshtt";
          #     repo = "rust-parallel";
          #     rev = "main"; # Specify a real version/tag
          #     sha256 = lib.fakeSha256;
          #   };
          #   cargoSha256 = lib.fakeSha256;
          # })
        ];

      in
      {
        devShells.default = pkgs.mkShell {
          name = "genkit-dev";

          packages = with pkgs; [
            # --- System Dependencies ---
            git
            gh
            curl
            ripgrep
            fd
            cmake
            google-cloud-sdk
            d2

            # --- Language Toolchains ---
            nodejs_23
            (nodePackages.pnpm.overrideAttrs (oldAttrs: {
              pname = "pnpm";
              version = pnpmVersion;
              src = fetchurl {
                url = "https://registry.npmjs.org/pnpm/-/pnpm-${pnpmVersion}.tgz";
                sha256 = "157g4z35x0ix96wz98f89n13d03yr5h11z07a0p9z3j8l9l8z28s"; # Hash for pnpm 10.2.0
              };
              buildInputs = (oldAttrs.buildInputs or []) ++ [ nodejs_23 ];
            }))
            uv

            # --- Tool Sets ---
            pythonEnv
          ] ++ goTools ++ rustTools;

          # --- Environment Setup ---
          shellHook = ''
            echo "Entering Genkit Nix development shell..."

            # Indicate project setup steps
            echo ""
            echo "--------------------------------------------------"
            echo " Genkit Dev Environment Ready!"
            echo ""
            echo " Recommended next steps:"
            echo "   1. Install Node.js dependencies: pnpm install"
            echo "   2. Setup project (builds, links): pnpm run setup"
            echo "   3. (Optional) Setup pre-commit hooks: captainhook install -f -c captainhook.json"
            echo "   4. (Optional) Setup commit template: git config commit.template .git/COMMIT_MESSAGE_TEMPLATE"
            echo "   5. (Optional) Create/activate Python venv: uv venv && source .venv/bin/activate"
            echo "--------------------------------------------------"
            echo ""
          '';
        };
      }
    );
}
