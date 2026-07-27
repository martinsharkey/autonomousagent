{ pkgs }: {
  pkgs = import pkgs;
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
  ];
}
