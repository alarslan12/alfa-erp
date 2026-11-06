# ALFACOPYCENTER Suite 2.0.0 — Windows release / acceptance

Status: **candidate** until the Windows build and offline contracts are green.
The v1.1.1 GitHub Release and production Firebase branch remain untouched
while the candidate is under review.

## What the single installer includes

| Component | EXE | Default |
|---|---|---|
| ALFA ERP Personel | Staff/AlfaERP.exe | Yes |
| ALFA ERP Yönetici | Owner/AlfaERPYonetici.exe | Optional — setup password + Firebase owner role |
| ALFA Banner Studio Pro 3.3 | BannerStudio/AlfaBannerStudio.exe | Yes |
| ALFA Print Surveillance 2.0.0 | PrintSurveillance/AlfaPrintSurveillance.exe | Yes |
| Print agent + supervisor | PrintAgent/AlfaPrintAgent.exe and PrintSupervisor/AlfaPrintSupervisor.exe | Optional task; checked in installer |

Each desktop app has its own transparent branded icon. The company mark is
placed in the installed Brand folder. Owner installation password gates
the selection but **cannot replace Firebase owner authorization**.

Installer path: `%LOCALAPPDATA%\Programs\ALFACOPYCENTER`.
Existing ERP v1 installations are preserved side-by-side during the
first v2 upgrade. Data stored outside installer folders remain preserved:
`%LOCALAPPDATA%\AlfaERP` (ERP orders/cache/print SQLite) and
`%LOCALAPPDATA%\ALFA_Banner_Studio_Pro` (covers/archive/drafts).
**Do not delete those folders when removing older desktop shortcuts.**

## Print monitoring and Windows rights

- The user-visible standalone print dashboard and the agent operate as
  the **current Windows user**. The installer is `PrivilegesRequired=lowest`.
- WinSpool reads jobs visible to that user only, without elevated printer
  access. No `SetJob`, no reprint, no delete, no service restart.
- `FindFirstPrinterChangeNotification` + bounded fallback reconciliation
  are used to monitor print queues without continuous high-rate polling.
- For an enabled login task, an HKCU Run entry starts one **supervisor**
  after the user logs in; supervisor keeps the user-mode collector running,
  protects against duplicate instances and restarts only the helper process
  after an unexpectedly stopped or stale collector.
- There is **no Windows service**, no system-wide autorun, no print driver
  hook, no kernel privileges, no bypass of printer permissions. The app
  cannot monitor with the PC turned off or before a Windows user session
  is available. Some remote printer drivers block Win32 RPC calls.
- IPP is opt-in to private local network endpoints. SNMPv2c is opt-in,
  carries a plaintext community over the LAN (encrypted at rest using
  Windows user DPAPI), and never sends customer data to Firebase.
- Windows `PagesPrinted`, IPP document/impression/media counters and SNMP
  lifetime counts **do not certify the last physical PDF page**.
  Interruption workflow presents observed counters and requires a human
  to confirm the last intact PDF page before preparing the next page range.
- The print dashboard includes **Sistem Kontrolü** to show Spooler status,
  startup registration, agent presence, last snapshot age and SQLite access.

## Catalog/Banner Studio

- Banner Studio 3.3 is a self-contained locally served editor (127.0.0.1).
  It requires no Python installation on the user's PC after PyInstaller build.
- Supports Excel catalog, user-uploaded cover ZIPs, 1–30 book layouts,
  color themes, per-cover edition/cost labels, separated prices,
  user logo and username, JPG/PNG HD export, persistent design archives.
- The original source spreadsheet is bundled as a sample. The user's
  own covers are imported locally, not silently sent anywhere.
- The requested separate WhatsApp/Telegram master-book catalog has been
  **cancelled**; no catalog-PDF generator is bundled as a separate app.

## Release gate

1. Windows Python syntax compilation, brand ICO generation,
   offline print-contract unit tests and PyInstaller builds must pass.
2. All six EXEs (owner, staff, banner, print, agent, supervisor)
   must exist in the Windows artifact; one Inno Setup EXE is required.
3. Banner Studio and Print Surveillance standalone EXEs must pass their
   offline `--self-check`.
4. SHA-256 manifest must match the published Setup binary.
5. Physical hardware tests (Windows spooler under multiple Epson/Canon
   devices, paper-out/disconnect, IPP/SNMP vendor reports, restart) remain
   **device-dependent and cannot be certified from cloud CI**.
   Until these pass, do not claim guaranteed 24/7 physical print progress.
6. A v1.1.1 to suite-v2 transition changes the EXE installation path;
   use the new Setup manually for the first migration to avoid an old
   updater relaunching v1.

No installer is allowed to reset Firebase, erase orders, delete printer
jobs, wipe local logs or uninstall previously used data silently.
