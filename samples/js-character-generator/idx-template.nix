{pkgs, language ? "js", tos ? "false", ... }: {  
  packages = [
    pkgs.nodejs
  ];
  bootstrap = ''
    mkdir "$out"
    mkdir "$out"/.idx
    cp -r ${./.idx}/. "$out/.idx/"
    cp -f ${./package.json} "$out/package.json"
    cp -f ${./package-lock.json} "$out/package-lock.json"
    cp -f ${./index.ts} "$out/index.ts"
    cp -f ${./.gitignore} "$out/.gitignore"
    cp ${./README_IDX.md} "$out"/README.md
    chmod -R u+w "$out"
  '';
}