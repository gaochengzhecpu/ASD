"""Expand the bundled public evidence once per server process."""
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

ARCHIVE=Path(__file__).resolve().parent/'evidence_bundle.zip'
_TEMP=tempfile.TemporaryDirectory(prefix='ema-cmc-evidence-')
EVIDENCE_ROOT=Path(_TEMP.name)
with zipfile.ZipFile(ARCHIVE) as archive:
    entries=archive.infolist()
    if sum(i.file_size for i in entries)>250_000_000:
        raise ValueError('Unexpected evidence bundle size')
    for item in entries:
        path=PurePosixPath(item.filename)
        if path.is_absolute() or '..' in path.parts or path.parts[0] not in {'data','assets'} or '\\' in item.filename:
            raise ValueError('Invalid evidence bundle path')
    archive.extractall(EVIDENCE_ROOT)
