
{ pkgs }: {
  deps = [
    pkgs.python3
    pkgs.tkinter
    pkgs.python3Packages.tkinter
    pkgs.libGLU
    pkgs.libGL
    pkgs.tesseract
    pkgs.libyaml
    pkgs.zlib
    pkgs.tk
    pkgs.tcl
    pkgs.libxcrypt
    pkgs.libwebp
    pkgs.libtiff
    pkgs.libjpeg
    pkgs.libimagequant
    pkgs.lcms2
    pkgs.loguru
    pkgs.xcbuild
    pkgs.swig
    pkgs.openjpeg
    pkgs.mupdf
    pkgs.libjpeg_turbo
    pkgs.jbig2dec
    pkgs.harfbuzz
    pkgs.gumbo
    pkgs.freetype
  ];
}
