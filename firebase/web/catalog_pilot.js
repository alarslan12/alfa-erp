// This is a read-only staging pilot, never the live ordering app.
// A single Firestore listener replaces repeated 2-second/30-second polling.
// Public catalogue queries must include is_active == true for Rules parity.
// Firebase JS SDK 13.2.0 was released Nov 2, 2026.
import { initializeApp } from "https://www.gstatic.com/firebasejs/13.2.0/firebase-app.js";
import { getFirestore, collection, query, where, onSnapshot }
  from "https://www.gstatic.com/firebasejs/13.2.0/firebase-firestore.js";
import { firebaseConfig, workspaceId } from "./config.js";

const app = initializeApp(firebaseConfig);
const firestore = getFirestore(app);
const statusNode = document.querySelector("#status");
const emptyNode = document.querySelector("#empty");
const catalogNode = document.querySelector("#catalog");
const searchNode = document.querySelector("#search");
let books = [];
let ready = false;

function render() {
  const term = searchNode.value.toLocaleLowerCase("tr").trim();
  const matches = books.filter(book =>
    [book.code, book.name, book.group_name]
      .join(" ").toLocaleLowerCase("tr").includes(term));
  const fragment = document.createDocumentFragment();
  for (const book of matches.slice(0, 200)) {
    const element = document.createElement("article");
    element.className = "book";
    const code = document.createElement("span");
    code.className = "code";
    code.textContent = String(book.code ?? "");
    const name = document.createElement("strong");
    name.className = "name";
    name.textContent = String(book.name ?? "İsimsiz kitap");
    const detail = document.createElement("span");
    detail.className = "detail";
    detail.textContent = [book.group_name || "Genel",
                          String(book.page_count ?? 0) + " sayfa",
                          book.supports_color ? "Renkli + S/B" : "S/B"]
      .join(" · ");
    element.append(code, name, detail);
    fragment.append(element);
  }
  catalogNode.replaceChildren(fragment);
  emptyNode.hidden = !ready || matches.length > 0;
  emptyNode.textContent = !books.length
    ? "Firestore'da henüz yayınlanmış kitap bulunmuyor. Kaynak veriler aktarılmadıysa bu beklenen bir durumdur."
    : "Aramayla eşleşen kitap bulunamadı.";
  statusNode.textContent = ready
    ? "Firestore bağlantısı aktif · " + books.length + " kitap · tek gerçek zamanlı dinleyici"
    : "Firestore bağlantısı hazırlanıyor…";
}
searchNode.addEventListener("input", render);

const q = query(
  collection(firestore, "workspaces", workspaceId, "books"),
  where("is_active", "==", true)
);
const stop = onSnapshot(q, snapshot => {
  ready = true;
  books = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }))
    .sort((a, b) => String(a.code ?? "").localeCompare(String(b.code ?? ""), "tr"));
  render();
}, error => {
  ready = false;
  books = [];
  catalogNode.replaceChildren();
  statusNode.textContent = "Firestore erişimi başarısız: " + String(error.code || "unknown");
  emptyNode.hidden = false;
  emptyNode.textContent =
    "Kurallar henüz yayımlanmamış, proje erişimi reddedilmiş veya veri yolu eksik olabilir. " +
    "Özel anahtarları bu sayfaya eklemeyin.";
});

window.addEventListener("pagehide", () => stop(), {once:true});
