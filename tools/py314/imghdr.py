# Shim imghdr (removido da stdlib no Python 3.13).
# Usado por stagger/yt_dlp (deps do Kanna-X). Implementa imghdr.what()
# com detecção por magic bytes para os formatos comuns.
# Instalado em site-packages pelo setup-kanna.sh.

__all__ = ["what", "whats"]

_TESTS = []


def _magic_jpeg(h, f):
    if h[:3] == b"\xff\xd8\xff":
        return "jpeg"


def _magic_png(h, f):
    if h[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"


def _magic_gif(h, f):
    if h[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"


def _magic_bmp(h, f):
    if h[:2] == b"BM":
        return "bmp"


def _magic_webp(h, f):
    if h[:4] == b"RIFF" and h[8:12] == b"WEBP":
        return "webp"


def _magic_tiff(h, f):
    if h[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"


_TESTS.extend(
    [_magic_jpeg, _magic_png, _magic_gif, _magic_bmp, _magic_webp, _magic_tiff]
)


def what(file, h=None):
    """Detecta o tipo de imagem. Compatível com imghdr.what()."""
    if h is None:
        if isinstance(file, str):
            with open(file, "rb") as f:
                h = f.read(32)
        else:
            pos = file.tell()
            h = file.read(32)
            file.seek(pos)
    for test in _TESTS:
        result = test(h, file)
        if result:
            return result
    return None


def whats(*args, **kwargs):  # pragma: no cover
    return what(*args, **kwargs)
