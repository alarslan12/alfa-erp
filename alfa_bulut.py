"""ALFA ERP V5.1: local files untouched; Supabase user-scoped REST access.

Uses only the public publishable key. Passwords and tokens stay in process memory.
No service role, database password or secret keys should be used by clients.
"""
from __future__ import annotations
import json
import time
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request

PROJECT_URL = 'https://gdfuljiyfvpjvokiarnx.supabase.co'
PUBLISHABLE_KEY = 'sb_publishable_lMvpER-_plYOePZ-2VNhXw_Lu83JHKw'
WORKSPACE_SLUG = 'alfa-erp'


class CloudError(RuntimeError):
    def __init__(self,message,retryable=False):
        super().__init__(message)
        self.retryable=bool(retryable)


class AlfaCloud:
    """Thin HTTP layer. No disk persistence of auth tokens or passwords."""

    def __init__(self):
        self._session = None
        self._expires = 0

    @property
    def logged_in(self):
        return bool(self._session and self._session.get('access_token'))

    def _http(self, method, path, payload=None, authenticated=False, extra_headers=None):
        url = PROJECT_URL.rstrip('/') + path
        headers = {'apikey': PUBLISHABLE_KEY, 'Accept': 'application/json'}
        if authenticated:
            self._renew_if_needed()
            if not self.logged_in:
                raise CloudError('Oturum açılmamış. Önce e-posta ve şifrenizle giriş yapın.')
            headers['Authorization'] = 'Bearer ' + self._session['access_token']
        if extra_headers:
            headers.update(extra_headers)
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as result:
                text = result.read().decode('utf-8')
                return json.loads(text) if text.strip() else None
        except urllib.error.HTTPError as error:
            message = f'Supabase HTTP {error.code}'
            try:
                data = json.loads(error.read().decode('utf-8'))
                message = data.get('msg') or data.get('message') or data.get('error_description') or data.get('error') or message
            except (ValueError, UnicodeError):
                pass
            # Never include bearer tokens, passwords or raw request headers in errors.
            raise CloudError(str(message)[:350]) from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            reason=getattr(error,'reason',error)
            if isinstance(reason,ssl.SSLError):
                hint='SSL sertifikası veya HTTPS doğrulaması'
            elif isinstance(reason,socket.gaierror):
                hint='DNS adresi çözümlenemedi'
            elif isinstance(reason,(TimeoutError,socket.timeout)) or 'timed out' in str(reason).lower():
                hint='Bağlantı zaman aşımı'
            elif isinstance(reason,ConnectionRefusedError):
                hint='Bağlantı reddedildi'
            else:
                hint=type(reason).__name__
            raise CloudError('Supabase bağlantısı kurulamadı ('+hint+
                             '). VPN, güvenlik duvarı ve DNS ayarlarını kontrol edin.',
                             retryable=True) from None

    def health(self):
        self._http('GET', '/auth/v1/health')
        return True

    def sign_up(self, email, password):
        if not email.strip() or len(password) < 8:
            raise CloudError('E-posta girin ve en az 8 karakterli bir parola seçin.')
        result = self._http('POST', '/auth/v1/signup', {'email': email.strip(), 'password': password})
        # Email confirmation can be required; signup does not imply membership.
        if isinstance(result, dict) and result.get('access_token'):
            self._install_session(result)
        return True

    def sign_in(self, email, password):
        if not email.strip() or not password:
            raise CloudError('E-posta ve parola gerekli.')
        result=None
        for attempt in range(2):
            try:
                result=self._http('POST','/auth/v1/token?grant_type=password',
                                  {'email':email.strip(),'password':password})
                break
            except CloudError as exc:
                if not exc.retryable or attempt:
                    raise
                time.sleep(0.7)
        self._install_session(result)
        return True

    def _install_session(self, data):
        if not isinstance(data, dict) or not data.get('access_token'):
            raise CloudError('Oturum açılamadı. E-posta doğrulamasını kontrol edin.')
        self._session = {
            'access_token': data['access_token'],
            'refresh_token': data.get('refresh_token'),
            'user': data.get('user', {}),
        }
        self._expires = time.monotonic() + max(60, int(data.get('expires_in', 3600)))

    def _renew_if_needed(self):
        if not self._session or time.monotonic() < self._expires - 90:
            return
        refresh = self._session.get('refresh_token')
        if not refresh:
            self.sign_out()
            raise CloudError('Oturum süresi doldu, yeniden giriş yapın.')
        response = self._http('POST', '/auth/v1/token?grant_type=refresh_token',
                              {'refresh_token': refresh})
        self._install_session(response)

    def sign_out(self):
        self._session = None
        self._expires = 0

    def get(self, table, query):
        if table not in ('workspaces', 'workspace_members', 'books', 'orders', 'order_items'):
            raise ValueError('Unsupported cloud query')
        return self._http('GET', f'/rest/v1/{table}?{query}', authenticated=True)

    def upload_catalog_first_time(self, workspace_id, books):
        """One-time initial catalog import only; existing cloud catalog is never overwritten."""
        if not books:
            raise CloudError('Katalog boş; aktarım yapılmadı.')
        current = self.get('books', 'select=id&workspace_id=eq.' + urllib.parse.quote(workspace_id) + '&limit=1')
        if current:
            raise CloudError('Bulut kataloğu boş değil. Veri değiştirilmedi; güncelleme için ayrı eşitleme gerekir.')
        data = [dict(workspace_id=workspace_id, code=str(item['kod']),
                     name=str(item['isim']), group_name=str(item.get('grup', '')),
                     page_count=int(item['sayfa']), supports_color=bool(item.get('renkli_opsiyon', False)))
                for item in books]
        if len({x['code'] for x in data}) != len(data):
            raise CloudError('Katalogda aynı kitap kodu birden fazla var; aktarım iptal edildi.')
        return self._http('POST', '/rest/v1/books', data, authenticated=True,
                          extra_headers={'Prefer':'return=minimal'})

    def read_status(self):
        rows = self.get('workspaces', 'select=id,name,slug&slug=eq.' + WORKSPACE_SLUG)
        if not rows:
            return {'access': False, 'message': 'Oturum açıldı; henüz ALFA ERP çalışma alanına erişim yetkisi verilmedi.'}
        ws = rows[0]
        members = self.get('workspace_members', 'select=role&workspace_id=eq.' + ws['id'])
        role = members[0].get('role', 'viewer') if members else 'viewer'
        books = self.get('books', 'select=id&workspace_id=eq.' + ws['id'] + '&limit=1000')
        orders = self.get('orders', 'select=id,status&workspace_id=eq.' + ws['id'] + '&deleted_at=is.null&limit=1000')
        return {'access': True, 'workspace_id': ws['id'], 'role': role,
                'books': len(books), 'orders': len(orders),
                'order_counts': {s: sum(x['status'] == s for x in orders)
                                 for s in ('havuz', 'aktif', 'tamamlandi')},
                'limited': len(books) >= 1000 or len(orders) >= 1000}

    def list_cloud_orders(self, workspace_id):
        """Read the newest 100 shared cloud orders. No local records are modified."""
        workspace = urllib.parse.quote(str(workspace_id), safe='')
        query = ('select=id,order_number,status,platform,shipping_reference,order_type,'
                 'gross_amount,shipping_fee,version,created_at,completed_at'
                 '&workspace_id=eq.' + workspace + '&deleted_at=is.null'
                 '&order=created_at.desc&limit=100')
        return self.get('orders', query)

    def list_mobile_inbox_orders(self, workspace_id):
        """Page through recent cloud orders so 100+ orders don't disappear from inbox."""
        workspace = urllib.parse.quote(str(workspace_id), safe='')
        result = []
        page_size = 200
        for offset in range(0, 5000, page_size):
            query = ('select=id,order_number,status,platform,shipping_reference,order_type,'
                     'gross_amount,shipping_fee,version,created_at,started_at,completed_at,'
                     'deleted_at'
                     '&workspace_id=eq.' + workspace + '&deleted_at=is.null'
                     '&order=created_at.desc,id.desc'
                     f'&limit={page_size}&offset={offset}')
            rows = self.get('orders', query)
            result.extend(rows)
            if len(rows) < page_size:
                return result
        raise CloudError('Bulutta 5000 üzerinde sipariş var; aktarım sayfalaması güncellenmeli.')

    def list_cloud_items(self, workspace_id, order_id):
        """Read *all* item lines; never import a partial order as complete.

        Orders may contain more than 300 separate book/print combinations.
        REST result ordering and paging are both explicit for consistent reads.
        """
        workspace = urllib.parse.quote(str(workspace_id), safe='')
        order = urllib.parse.quote(str(order_id), safe='')
        result = []
        page_size = 200
        for offset in range(0, 5000, page_size):
            query = ('select=id,book_code,book_name_snapshot,print_type,quantity,'
                     'prepared_count,boxed_count&workspace_id=eq.' + workspace
                     + '&order_id=eq.' + order
                     + '&order=book_code.asc,id.asc'
                     + f'&limit={page_size}&offset={offset}')
            rows = self.get('order_items', query)
            result.extend(rows)
            if len(rows) < page_size:
                return result
        raise CloudError('Siparişte 5000 üzerinde kitap satırı var; eksik sipariş aktarılmadı.')

    def cloud_order_action(self, workspace_id, order_id, expected_version, action,
                           item_id=None, prepared=None, boxed=None, shipping_fee=None):
        """PostgreSQL transaction with stale-version rejection and RLS authorization."""
        if action not in ('start','back_to_pool','finish','reopen','set_counts'):
            raise CloudError('Bilinmeyen bulut işlemi')
        args = {
            'p_workspace_id': str(workspace_id),
            'p_order_id': str(order_id),
            'p_expected_version': int(expected_version),
            'p_action': action,
            'p_item_id': str(item_id) if item_id else None,
            'p_prepared': prepared,
            'p_boxed': boxed,
            'p_shipping_fee': shipping_fee,
        }
        return self._http('POST', '/rest/v1/rpc/alfa_order_action',args,authenticated=True)
