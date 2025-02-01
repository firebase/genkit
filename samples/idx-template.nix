{pkgs, sample ? "js-character-generator", ...}: {
    packages = [
        pkgs.nodejs
    ];
    bootstrap = ''
        mkdir "$out"
        cp -rf ${./.}/${sample}/* "$out"
        ${if sample == "js-character-generator" then "" else "mkdir \"\$out\"/.idx"}
        ${if sample == "js-character-generator" then "" else "cp \${./dev-js-gemini.nix} \"\$out\"/.idx/dev.nix" }
        chmod -R u+w "$out"
    '';
}