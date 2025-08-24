# 🤖 Electronic Court Filling Automation

This project automates **submission of civil cases** in the **electronic court system**, combining **UI interaction**, **file handling**, and **database updates**.

It is used in production for handling real debtor cases. Some data is confidential. Not for public execution.

---

## 🚀 Project Overview

The automation pipeline includes:

- ✅ Automated case creation in electronic court, including multi-page form filling  
- ✅ Upload of supporting documents based on debtor ID  
- ✅ Token/session persistence to avoid repeated logins  
- ✅ Retry mechanisms for unstable UI interactions  
- ✅ Logging and exception handling for debugging  
- ✅ Excel export of failed records for review  
- ✅ Database updates marking successfully processed debtors  

---

## 🛠️ Tech Stack

| Tool / Library         | Purpose |
|------------------------|---------|
| **Python 3.x**         | Core language |
| **Selenium WebDriver** | Browser UI automation |
| **PyAutoGUI**          | File upload automation via keyboard/mouse simulation |
| **Pandas**             | Excel read/write for problem records |
| **SQLAlchemy**         | ORM for database updates |
| **Logging**            | Centralized logs |
| **Pickle**             | Token persistence for session reuse |

---

## 📂 Project Structure (Key Components)

| File / Class | Description |
|--------------|-------------|
| `Filling***Bot` | Main bot for interacting with electronic court, filling forms, uploading documents |
| `UpdateDebtorStatus` | Updates database records after successful case creation |
| `GetDataDBDebtors` | Retrieves debtor data from database for automation |
| `run()` | Entry point for executing the full automation flow |
| `write_problem_dicts_to_excel()` | Exports problematic records to Excel for manual review |
| `wait_and_*` methods | Utility functions with retry decorators for robust UI interaction |

---

## 🧪 Automation Features

- 🔁 **Retry decorators (`@retry_on_error`)** to repeat unstable UI actions  
- ⏳ **Explicit waits (`WebDriverWait`)** for clickability, visibility, and element presence  
- 💾 **Session/token reuse** with saving and loading token from `token.pkl`  
- 🗃️ **Database updates** through `UpdateDebtorStatus` to mark successfully processed records  
- 📋 **Excel export of problematic rows** via `write_problem_dicts_to_excel()`  
- 📂 **Automated file uploads** based on folder structure per debtor ID  
- 🖱️ **Multi-page form filling** (7 pages with different field types and branching logic)  
- 📅 **Calendar interaction** for selecting dates in forms  
- ⌨️ **Keyboard input emulation** using PyAutoGUI and Selenium for complex elements  
- ⚡ **Parallel execution / timeout handling** using `concurrent.futures.ThreadPoolExecutor`  
- 🔍 **Dynamic option selection** with fallback for partial string match (for complex dropdowns)  
- 🧩 **Conditional logic in form filling**, e.g., selecting fields based on bank or plaintiff type  
- 🛡️ **Robust exception handling** with logging and saving problematic data  
- 🌐 **URL checks** to ensure correct navigation and successful page transitions  
