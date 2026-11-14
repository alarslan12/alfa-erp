"""Small, private Kargonomi PDF slips (no Storage billing or public links)."""
from __future__ import annotations

import base64
import hashlib
import os
import tempfile
from pathlib import Path
import re
import uuid

from utils import tr_kucult

MAX_LABEL_BYTES = 512 * 1024


def requires_label(order):
    """The requirement follows the actual open-address order, not its fee."""
    platform = tr_kucult(order.get('platform') or '')
    kind = tr_kucult(order.get('order_type') or order.get('siparis_turu') or '')
    return 'acik adres' in platform or 'acik adres' in kind


def label_ready(order):
    if not requires_label(order):
        return True
    label = order.get('shipping_label') or {}
    receipt = order.get('shipping_label_receipt') or {}
    revision = label.get('revision') if isinstance(label, dict) else None
    return bool(revision and isinstance(receipt, dict)
                and receipt.get('revision') == revision
                and receipt.get('downloaded_by') and receipt.get('downloaded_at'))


def checked_id(value):
    value = str(value or '')
    if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value):
        raise ValueError('Önce siparişin Firebase eşitlenmesini bekle.')
    return value


def encode_pdf(path):
    path = Path(path)
    if path.suffix.lower() != '.pdf':
        raise ValueError('Yalnızca PDF kargo fişi seçilebilir.')
    with path.open('rb') as stream:
        raw = stream.read(MAX_LABEL_BYTES + 1)
    if len(raw) > MAX_LABEL_BYTES:
        raise ValueError('Kargo fişi en fazla 512 KB olabilir. PDF dosyasını küçült.')
    if not raw.startswith(b'%PDF-'):
        raise ValueError('Geçerli bir PDF kargo fişi seç.')
    name = path.name.replace('\\', '_').replace('/', '_')[:140]
    name = re.sub(r'[\x00-\x1f\x7f]', '_', name)
    if not name.lower().endswith('.pdf'):
        name = name[:136] + '.pdf'
    return {'revision': str(uuid.uuid4()), 'filename': name,
            'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'payload': base64.b64encode(raw).decode('ascii')}


def decode_pdf(record, label):
    if not isinstance(record, dict) or not isinstance(label, dict):
        raise ValueError('Fiş bulunamadı.')
    payload = record.get('payload')
    if not isinstance(payload, str) or len(payload) > 699052:
        raise ValueError('Fiş dosyası boyutu geçersiz.')
    try:
        raw = base64.b64decode(payload, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError('Fiş dosyası bozuk.') from exc
    digest = hashlib.sha256(raw).hexdigest()
    if (not raw.startswith(b'%PDF-') or len(raw) > MAX_LABEL_BYTES
            or len(raw) != label.get('size') or digest != label.get('sha256')
            or record.get('sha256') != digest):
        raise ValueError('Fiş bütünlük doğrulaması başarısız.')
    return raw


def save_pdf_atomic(path, content):
    path = Path(path)
    if path.suffix.lower() != '.pdf':
        raise ValueError('Dosya adının uzantısı .pdf olmalı.')
    fd, name = tempfile.mkstemp(dir=str(path.parent), prefix='.alfa_fis_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
