"""Owner-only outsourcing orders. Separate SQLite; no ERPDatabase or cloud calls."""
from contextlib import closing, contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
import sqlite3


def _now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def _amount_cents(value):
    try:
        amount = Decimal(str(value).replace(',', '.'))
        if not amount.is_finite() or not 0 <= amount < 1_000_000_000:
            raise ValueError('Ciro geçerli aralıkta değil.')
        return int((amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('Ciro sayısal olmalı.') from exc


def order_totals(orders):
    result = dict(siparis=0, kitap=0, sayfa=0, ciro_kurus=0)
    for order in orders:
        result['siparis'] += 1
        result['ciro_kurus'] += order['ciro_kurus']
        for item in order['kitaplar']:
            result['kitap'] += item['adet']
            result['sayfa'] += item['adet'] * item['sayfa_birim']
    return result


def local_label(sid):
    return f'D{int(sid):03d}'


class DerlemeHavuzu:
    """Local persistent snapshots. A ZIP export never marks a job completed."""
    def __init__(self, data_dir):
        self.path = Path(data_dir) / 'owner_derleme' / 'siparisler.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kod TEXT NOT NULL, ciro_kurus INTEGER NOT NULL,
                order_note TEXT NOT NULL, kitaplar TEXT NOT NULL,
                created_at TEXT NOT NULL, completed_at TEXT,
                last_zip_at TEXT, last_zip_path TEXT, deleted_at TEXT
            )""")
            db.execute('BEGIN IMMEDIATE')
            if 'deleted_at' not in {row[1] for row in db.execute('PRAGMA table_info(orders)')}:
                db.execute('ALTER TABLE orders ADD COLUMN deleted_at TEXT')

    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.row_factory = sqlite3.Row
            yield db

    @staticmethod
    def _snapshot(items, catalog, previous=()):
        old = {(str(item['kod']), item['tur']): item for item in previous}
        result = {}
        for item in items:
            code = str(item.get('kod', '')).strip()
            kind = str(item.get('tur', '')).upper()
            book = catalog.get(code)
            key = (code, kind)
            saved = old.get(key)
            if (book is None and saved is None) or kind not in ('SB', 'RNK'):
                raise ValueError('Kitap kodu veya baskı türü geçersiz.')
            if kind == 'RNK' and saved is None and not book.get('renkli_opsiyon'):
                raise ValueError(f'#{code}: renkli baskı seçeneği yok.')
            qty = int(item.get('adet', 0))
            if not 1 <= qty <= 100000:
                raise ValueError('Adet 1–100000 aralığında olmalı.')
            if key not in result:
                if saved is not None:
                    result[key] = dict(saved, adet=0)
                else:
                    pages = max(0, int(book.get('sayfa') or 0))
                    result[key] = dict(kod=code, tur=kind, adet=0,
                                       isim=str(book.get('isim') or code),
                                       sayfa=pages, sayfa_birim=pages)
            result[key]['adet'] += qty
            if result[key]['adet'] > 100000:
                raise ValueError('Toplam kitap adedi 100000 sınırını aşıyor.')
        if not result:
            raise ValueError('En az bir kitap seçilmeli.')
        return list(result.values())

    def add(self, info, items, catalog):
        books = self._snapshot(items, catalog)
        cents = _amount_cents(info.get('ciro', 0))
        with self._connection() as db:
            cursor = db.execute("""INSERT INTO orders
                (kod, ciro_kurus, order_note, kitaplar, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (str(info.get('kod') or '').strip()[:500], cents,
                 str(info.get('order_note') or '').strip()[:2000],
                 json.dumps(books, ensure_ascii=False), _now()))
            return cursor.lastrowid

    @staticmethod
    def _decode(row):
        order = dict(row)
        order['kitaplar'] = json.loads(order['kitaplar'])
        return order

    def list(self, completed=False):
        clause = 'IS NOT NULL' if completed else 'IS NULL'
        sort = 'completed_at DESC, id DESC' if completed else 'id DESC'
        with self._connection() as db:
            return [self._decode(row) for row in db.execute(
                f'SELECT * FROM orders WHERE deleted_at IS NULL AND completed_at {clause} ORDER BY {sort}')]

    def get(self, sid):
        with self._connection() as db:
            row = db.execute('SELECT * FROM orders WHERE id=? AND deleted_at IS NULL', (sid,)).fetchone()
        if row is None:
            raise ValueError('Yerel derleme siparişi bulunamadı.')
        return self._decode(row)

    def set_completed(self, sid, completed):
        self.set_completed_many([sid], completed)

    def set_completed_many(self, ids, completed):
        ids = list(dict.fromkeys(ids))
        with self._connection() as db:
            stamp = _now() if completed else None
            for sid in ids:
                cursor = db.execute(
                    'UPDATE orders SET completed_at=? WHERE id=? AND deleted_at IS NULL AND completed_at '
                    + ('IS NULL' if completed else 'IS NOT NULL'), (stamp, sid))
                if cursor.rowcount != 1:
                    raise ValueError('Sipariş bulunamadı veya durumu zaten değişti.')

    def update(self, sid, info, items, catalog, *, expected=None):
        cents = _amount_cents(info.get('ciro', 0))
        code = str(info.get('kod') or '').strip()[:500]
        note = str(info.get('order_note') or '').strip()[:2000]
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM orders WHERE id=? AND deleted_at IS NULL', (sid,)).fetchone()
            if row is None:
                raise ValueError('Yerel derleme siparişi bulunamadı.')
            order = self._decode(row)
            if expected is not None and order != expected:
                raise ValueError('Sipariş değişmiş. Yenileyip tekrar düzenleyin.')
            books = self._snapshot(items, catalog, order['kitaplar'])
            changed = (code != order['kod'] or note != order['order_note'] or books != order['kitaplar'])
            db.execute('''UPDATE orders SET kod=?, ciro_kurus=?, order_note=?, kitaplar=?,
                last_zip_at=?, last_zip_path=? WHERE id=?''',
                (code, cents, note, json.dumps(books, ensure_ascii=False),
                 None if changed else order['last_zip_at'],
                 None if changed else order['last_zip_path'], sid))

    def delete_many(self, ids):
        # Soft delete: hide records from both groups, keep historical data and IDs.
        with self._connection() as db:
            stamp = _now()
            for sid in dict.fromkeys(ids):
                cursor = db.execute('UPDATE orders SET deleted_at=? WHERE id=? AND deleted_at IS NULL', (stamp, sid))
                if cursor.rowcount != 1:
                    raise ValueError('Sipariş bulunamadı veya zaten silinmiş.')

    def record_zip(self, sid, path, *, expected=None):
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if expected is not None:
                row = db.execute('SELECT * FROM orders WHERE id=? AND deleted_at IS NULL', (sid,)).fetchone()
                if row is None or any(self._decode(row)[key] != expected[key] for key in ('kod', 'order_note', 'kitaplar')):
                    raise ValueError('Sipariş derleme sırasında değişti; yeni ZIP gerekiyor.')
            cursor = db.execute(
                'UPDATE orders SET last_zip_at=?, last_zip_path=? WHERE id=? AND deleted_at IS NULL',
                (_now(), str(path), sid))
            if cursor.rowcount != 1:
                raise ValueError('Derleme siparişi bulunamadı.')


def compile_snapshot(order):
    """Use stored book titles/pages, not subsequently changed catalog entries."""
    label = local_label(order['id'])
    reference = order.get('kod', '').strip()
    snapshot = dict(id=order['id'], kod=label + (' / ' + reference if reference else ''),
                    order_note=order.get('order_note', ''),
                    kitaplar=[dict(item) for item in order['kitaplar']],
                    local_derleme=True)
    catalog = {item['kod']: dict(isim=item['isim'], sayfa=item['sayfa_birim'])
               for item in order['kitaplar']}
    return snapshot, catalog
