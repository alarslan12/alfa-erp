// Firebase emulator only: no production credentials, URLs or customer data.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { initializeTestEnvironment, assertFails, assertSucceeds } =
  require('@firebase/rules-unit-testing');

async function run() {
  if (!process.env.FIREBASE_DATABASE_EMULATOR_HOST) {
    throw new Error('Refusing to run without RTDB emulator');
  }
  const env = await initializeTestEnvironment({
    projectId: 'demo-alfa-labels',
    database: { rules: fs.readFileSync('firebase/database.rules.json', 'utf8') },
  });
  const root = 'alfa/ci-workspace';
  const o1 = crypto.randomUUID(), o2 = crypto.randomUUID(),
    normal = crypto.randomUUID(), legacy = crypto.randomUUID();
  const original = (id, number, platform='Açık Adres / Manuel', status='aktif') => ({
    id, status, platform, version:1, order_number:number,
    shipping_reference:'Synthetic address', order_type:'Normal Sipariş'
  });
  const a1 = original(o1, 1), a2 = original(o2, 2);
  const plain = original(normal, 3, 'Dolap');
  const old = original(legacy, 4, 'Açık Adres', 'tamamlandi');
  try {
    await env.clearDatabase();
    await env.withSecurityRulesDisabled(async ctx => {
      await ctx.database().ref(root).set({
        members:{'ci-owner':{active:true,role:'owner'},
          'ci-staff':{active:true,role:'staff'},
          'ci-inactive':{active:false,role:'staff'}},
        orders:{[o1]:a1,[o2]:a2,[normal]:plain,[legacy]:old}
      });
    });
    const owner = env.authenticatedContext('ci-owner').database();
    const staff = env.authenticatedContext('ci-staff').database();
    const inactive = env.authenticatedContext('ci-inactive').database();
    const anon = env.unauthenticatedContext().database();
    const ref = (db, id) => db.ref(root + '/orders/' + id);
    const blobRef = (db,id,revision) => db.ref(root + '/shipping_label_files/' + id + '/' + revision);
    const raw = Buffer.from('%PDF-1.4\n%%EOF\n');
    const blob = {size:raw.length, payload:raw.toString('base64'),
      sha256:crypto.createHash('sha256').update(raw).digest('hex')};
    const label = () => ({
      revision:crypto.randomUUID(), size:blob.size, sha256:blob.sha256,
      filename:'test.pdf', uploaded_by:'ci-owner', uploaded_at:'2026-01-01T00:00:00Z'
    });
    const receipt = (l, uid='ci-staff') => ({
      revision:l.revision, downloaded_by:uid, downloaded_at:'2026-01-01T00:01:00Z'
    });
    const l1 = label();
    await assertFails(ref(staff,o1).set({...a1,version:2,status:'tamamlandi'}));
    await assertFails(blobRef(staff,o1,l1.revision).set(blob));
    await assertFails(blobRef(anon,o1,l1.revision).set(blob));
    await assertFails(ref(owner,o1).set({...a1,version:2,shipping_label:l1}));
    await assertSucceeds(blobRef(owner,o1,l1.revision).set(blob));
    await assertFails(blobRef(staff,o1,l1.revision).once('value'));
    await assertFails(ref(staff,o1).set({...a1,version:2,shipping_label:l1}));
    const attached = {...a1,version:2,shipping_label:l1};
    await assertSucceeds(ref(owner,o1).set(attached));
    await assertFails(blobRef(anon,o1,l1.revision).once('value'));
    await assertFails(blobRef(inactive,o1,l1.revision).once('value'));
    const downloaded = await assertSucceeds(blobRef(staff,o1,l1.revision).once('value'));
    assert.equal(downloaded.val().sha256,blob.sha256);
    await assertFails(ref(staff,o1).set({...attached,version:3,status:'tamamlandi'}));
    await assertFails(ref(owner,o1).set({...attached,version:3,shipping_label_receipt:receipt(l1,'ci-owner')}));
    await assertFails(ref(staff,o1).set({...attached,version:3,shipping_label_receipt:receipt(l1,'other')}));
    await assertFails(ref(staff,o1).set({...attached,version:3,shipping_label_receipt:receipt(label())}));
    const confirmed = {...attached,version:3,shipping_label_receipt:receipt(l1)};
    await assertSucceeds(ref(staff,o1).set(confirmed));
    await assertFails(blobRef(owner,o1,l1.revision).remove());
    await assertFails(ref(staff,o1).set({...confirmed,version:4,shipping_reference:'changed'}));
    await assertSucceeds(ref(staff,o1).set({...confirmed,version:4,status:'tamamlandi'}));
    // Replacing a live slip resets the acknowledgement, and old payload is inaccessible.
    const first = label(); await assertSucceeds(blobRef(owner,o2,first.revision).set(blob));
    const v2 = {...a2,version:2,shipping_label:first};
    await assertSucceeds(ref(owner,o2).set(v2));
    const v3 = {...v2,version:3,shipping_label_receipt:receipt(first)};
    await assertSucceeds(ref(staff,o2).set(v3));
    const next = label(); await assertSucceeds(blobRef(owner,o2,next.revision).set(blob));
    await assertFails(ref(owner,o2).set({...v3,version:4,shipping_label:next}));
    const v4 = {...v2,version:4,shipping_label:next};
    await assertSucceeds(ref(owner,o2).set(v4));
    await assertFails(blobRef(staff,o2,first.revision).once('value'));
    await assertSucceeds(blobRef(owner,o2,first.revision).remove());
    await assertFails(ref(staff,o2).set({...v4,version:5,status:'tamamlandi'}));
    await assertSucceeds(ref(owner,o2).set({...a2,version:5,shipping_reference:'New synthetic address'}));
    // Existing non-address and historical completed order behavior is unchanged.
    await assertSucceeds(ref(staff,normal).set({...plain,version:2,status:'tamamlandi'}));
    await assertSucceeds(ref(owner,legacy).set({...old,version:2}));
    console.log('Shipping label Firebase rule authorization and transitions passed.');
  } finally { await env.cleanup(); }
}
run().catch(error => { console.error(error); process.exitCode=1; });
