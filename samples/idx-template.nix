{pkgs, sample ? "js-character-generator", ...}: {
    packages = [
        pkgs.nodejs
    ];
    bootstrap = ''
        mkdir "$out"
        cp -rf ${./.}/${sample}/* "$out"
        mkdir "$out"/.idx
        cp ${./dev-js-gemini.nix} "$out"/.idx/dev.nix
        chmod -R u+w "$out"
    '';
}