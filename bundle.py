"""Lazily expand immutable evidence outside Python module import / hot reload.

The content-addressed cache outlives module eviction. A TemporaryDirectory owned by
a module can otherwise remove files still used by another Streamlit session.
"""
from pathlib import Path, PurePosixPath
import hashlib
import threading
import tempfile
import zipfile

ARCHIVE=Path(__file__).resolve().parent/'evidence_bundle.zip'
ARCHIVES=[p for p in [ARCHIVE,ARCHIVE.with_name('semantic_bundle.zip')] if p.exists()]
_digest=hashlib.sha256()
for _path in ARCHIVES:
    with _path.open('rb') as _file:
        for _block in iter(lambda:_file.read(1024*1024),b''):_digest.update(_block)
EVIDENCE_ROOT=Path(tempfile.gettempdir())/('ema-cmc-evidence-'+_digest.hexdigest()[:24])
_lock=threading.Lock()


def ensure_bundle():
    if (EVIDENCE_ROOT/'.ready').exists():return EVIDENCE_ROOT
    with _lock:
        if (EVIDENCE_ROOT/'.ready').exists():return EVIDENCE_ROOT
        with tempfile.TemporaryDirectory(prefix='ema-cmc-unpack-') as temporary:
            staging=Path(temporary)/'content';staging.mkdir()
            for archive_path in ARCHIVES:
                with zipfile.ZipFile(archive_path) as archive:
                    entries=archive.infolist()
                    if sum(i.file_size for i in entries)>250_000_000:
                        raise ValueError('Unexpected evidence bundle size')
                    for item in entries:
                        path=PurePosixPath(item.filename)
                        if path.is_absolute() or '..' in path.parts or path.parts[0] not in {'data','assets'} or '\\' in item.filename:
                            raise ValueError('Invalid evidence bundle path')
                    archive.extractall(staging)
            (staging/'.ready').write_text(_digest.hexdigest(),encoding='ascii')
            try:staging.rename(EVIDENCE_ROOT)
            except OSError:
                # A concurrent process may have atomically published the identical cache.
                if not (EVIDENCE_ROOT/'.ready').exists():raise
    return EVIDENCE_ROOT
