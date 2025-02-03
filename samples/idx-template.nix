{pkgs, sample ? "js-character-generator", ...}: {
    packages = [
        pkgs.nodejs
    ];
    bootstrap = ''
        mkdir "$out"
        cp -rf ${./.}/${sample}/* "$out"
        chmod -R u+w "$out"
    '';
}