"""Cloud label operations; all authorization is also enforced by RTDB Rules."""
from datetime import datetime, timezone
import socket
import uuid

from kargo_etiketi import checked_id, decode_pdf, encode_pdf, label_ready, requires_label, save_pdf_atomic
from alfa_rtdb import DeviceError


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _role(client):
    member = client._get('members/' + str(client.uid)) or {}
    role = member.get('role')
    if member.get('active') is not True or role not in ('owner', 'staff'):
        raise DeviceError('Cihazın kargo fişi yetkisi yok.', 403)
    return role


def _order(client, order_id, reference):
    row = client._get('orders/' + order_id)
    if not isinstance(row, dict) or row.get('deleted_at'):
        raise DeviceError('Bulut siparişi bulunamadı.', 409)
    if not requires_label(row) or str(row.get('shipping_reference') or '') != reference:
        raise DeviceError('Sipariş adresi değişmiş; siparişi yenile.', 409)
    return row


def _audit(row, client, action, revision):
    event = str(uuid.uuid4())
    now = _now()
    row['updated_at'] = now
    row.setdefault('event_log', {})[event] = {
        'id': event, 'action': action, 'device_id': client.uid,
        'device_name': socket.gethostname()[:120], 'order_ids': [row['id']],
        'created_at': now, 'details': {'revision': revision}}
    row['version'] = int(row.get('version') or 0) + 1


def _remove_unused(client, path):
    # Rules refuse to delete an attachment still referenced by the order.
    # A cleanup failure never invalidates a successfully uploaded label.
    try:
        client._request('DELETE', path)
    except Exception:
        pass


def upload_label(client, order_id, reference, filename):
    order_id = checked_id(order_id)
    if _role(client) != 'owner':
        raise DeviceError('Kargo fişi yüklemek için yönetici yetkisi gerekli.', 403)
    before = _order(client, order_id, reference)
    if before.get('status') not in ('havuz', 'aktif'):
        raise DeviceError('Tamamlanan siparişin fişi değiştirilemez.', 422)
    old_revision = (before.get('shipping_label') or {}).get('revision')
    record = encode_pdf(filename)
    revision = record['revision']
    path = 'shipping_label_files/' + order_id + '/' + revision
    label = {k: record[k] for k in ('revision','filename','size','sha256')}
    label.update(uploaded_by=client.uid, uploaded_at=_now())
    blob = {k: record[k] for k in ('payload','sha256','size')}
    # Immutable file revision first, then conditional order metadata update.
    # No full PDF is ever written inside orders or broadcast in an order pull.
    try:
        client._request('PUT', path, blob, match='null_etag', timeout=45)

        def mutate(row):
            if (not isinstance(row, dict) or row.get('deleted_at')
                    or row.get('status') not in ('havuz','aktif')
                    or not requires_label(row)
                    or str(row.get('shipping_reference') or '') != reference
                    or (row.get('shipping_label') or {}).get('revision') != old_revision):
                raise DeviceError('Sipariş veya fiş değişmiş; yenileyip tekrar yükle.', 409)
            row['shipping_label'] = label
            row.pop('shipping_label_receipt', None)
            _audit(row, client, 'shipping_label_uploaded', revision)
            return row, label
        client._atomic_order(order_id, mutate)
    except Exception:
        _remove_unused(client, path)
        raise
    if old_revision and old_revision != revision:
        try:
            old_path = 'shipping_label_files/' + order_id + '/' + checked_id(old_revision)
            _remove_unused(client, old_path)
        except ValueError:
            pass
    return label


def download_label(client, order_id, reference, filename):
    order_id = checked_id(order_id)
    role = _role(client)
    before = _order(client, order_id, reference)
    label = before.get('shipping_label')
    if not isinstance(label, dict):
        raise ValueError('Yönetici henüz kargo fişi yüklemedi.')
    revision = checked_id(label.get('revision'))
    path = 'shipping_label_files/' + order_id + '/' + revision
    body = client._request('GET', path, timeout=45)[0]
    raw = decode_pdf(body, label)
    save_pdf_atomic(filename, raw)
    # An owner can inspect/download the file, but this does not substitute
    # for the staff's acknowledgement. Record only after an atomic local save.
    if role == 'staff' and before.get('status') in ('havuz','aktif'):
        def mutate(row):
            if (not isinstance(row, dict) or row.get('deleted_at')
                    or not requires_label(row)
                    or str(row.get('shipping_reference') or '') != reference
                    or (row.get('shipping_label') or {}).get('revision') != revision):
                raise DeviceError('Fiş indirildi ancak bu sırada yenisi yüklendi. Yeni fişi indir.', 409)
            if label_ready(row):
                return None, True
            if row.get('status') not in ('havuz','aktif'):
                raise DeviceError('Fiş kaydedildi fakat sipariş durumu değişti; yenile.',409)
            row['shipping_label_receipt'] = {'revision': revision,
                  'downloaded_by': client.uid, 'downloaded_at': _now()}
            _audit(row, client, 'shipping_label_downloaded', revision)
            return row, True
        client._atomic_order(order_id, mutate)
    return {'acknowledged': role == 'staff'}
