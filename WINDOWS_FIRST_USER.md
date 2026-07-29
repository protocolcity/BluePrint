# BluePrint on Windows — first time (nothing installed)

Hand this page to someone on a blank Windows PC.  
**Goal:** suite open in the browser at `http://127.0.0.1:8801/`.

You need about **10 minutes**, internet, and admin rights only if the Python installer asks.

---

## Step 1 — Install Python (once)

1. Open: [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
2. Download **Python 3.12** (or any **3.11+**).
3. Run the installer.
4. **Check this box before continuing:**  
   **Add python.exe to PATH**
5. Click **Install Now**.
6. When it finishes: **close PowerShell if it was open**, then open a **new** PowerShell window  
   (search “PowerShell” in the Start menu).

**Optional (Windows 11):** if you prefer the terminal:

```powershell
winget install Python.Python.3.12 --accept-package-agreements
```

Then close PowerShell and open a new one.

---

## Step 2 — Install BluePrint and start it

In the **new** PowerShell window, **copy everything below**, paste, press **Enter**:

```powershell
py -3 -m pip install --upgrade pip
py -3 -m pip install --upgrade "protocolcity[engines]"
blueprint setup "$env:USERPROFILE\BluePrint" --create --yes
blueprint serve --root "$env:USERPROFILE\BluePrint"
```

If PowerShell says `blueprint` is not recognized, Scripts is not on PATH — use the
**package module** form (same program, not a second product name):

```powershell
py -3 -m protocolcity setup "$env:USERPROFILE\BluePrint" --create --yes
py -3 -m protocolcity serve --root "$env:USERPROFILE\BluePrint"
```

Wait until install finishes and the last command stays running (the suite is the process that does not return to a prompt).

---

## Step 3 — Open the map

In your browser (Chrome, Edge, Firefox), go to:

**http://127.0.0.1:8801/**

You should see the BluePrint **Overview**. Click **Map** to dig into the workspace.

| Keep open | Leave the PowerShell window open while you use the suite. |
| Stop | Click the PowerShell window and press **Ctrl+C**. |
| Workspace folder | `C:\Users\<you>\BluePrint` (created for you) |

If Windows Firewall asks about Python / private networks: **Allow**.

---

## If a command fails

| Message / symptom | Fix |
|---|---|
| `py` is not recognized | Python not on PATH. Reinstall Python and tick **Add python.exe to PATH**, then open a **new** PowerShell. Or try the same lines with `python` instead of `py -3`. |
| `No module named protocolcity` | Install did not finish — re-run the three `pip` / `setup` / `serve` lines. |
| Browser cannot connect | Make sure `serve` is still running in PowerShell; wait ~15s after start; try `http://127.0.0.1:8801/` again. |
| Page loads but Map looks empty | Normal for a brand-new workspace. Overview still works; add folders later. |
| Want a different folder name | Change `BluePrint` in both the `setup` and `serve` lines to any path you own. |

---

## Next time (already installed)

Open PowerShell and run only:

```powershell
blueprint serve --root "$env:USERPROFILE\BluePrint"
# or: py -3 -m protocolcity serve --root "$env:USERPROFILE\BluePrint"
```

Then open **http://127.0.0.1:8801/** again.

---

## Optional: one script file

If you were given `install_windows.ps1`:

```powershell
powershell -ExecutionPolicy Bypass -File install_windows.ps1
```

Same outcome: install packages → create workspace → start suite.

---

## What you installed (for the curious)

| Piece | Role |
|---|---|
| **BluePrint** (`protocolcity` package) | Map + CLI (`blueprint` / `protocolcity`) |
| **WorkLane** | Work orders (tickets) |
| **WorkForce** | Hired agents / jobs |

No Homebrew, no Git clone, no WSL required for this path.
