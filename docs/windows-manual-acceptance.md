# Windows manual acceptance

- Target: Windows x86_64 graphical desktop
- Current evidence: none
- Overall state: `BLOCKED` until a real Windows machine is available

Windows GitHub Actions can prove compilation, automated tests, Sidecar health
and installer generation. It cannot prove graphical installation, tray,
notification, autostart or uninstall behaviour. A human tester must record the
application version, artifact SHA256, Windows version, machine architecture,
date, steps, result and screenshots/logs for every item below.

| # | Manual check | State | Required evidence |
| --- | --- | --- | --- |
| 1 | Installer starts | BLOCKED | Screenshot and installer log |
| 2 | Install path is correct | BLOCKED | Installed path screenshot |
| 3 | Double-click opens the app | BLOCKED | Screenshot and app log |
| 4 | App runs without system Python or Node | BLOCKED | Clean-machine software list and launch log |
| 5 | WebView2 renders the UI | BLOCKED | Screenshot |
| 6 | Tray icon appears in notification area | BLOCKED | Screenshot |
| 7 | Closing the window hides it to tray | BLOCKED | Screen recording or paired screenshots |
| 8 | Background monitoring continues while hidden | BLOCKED | Timestamped monitor events |
| 9 | Tray activation restores the window | BLOCKED | Screen recording or paired screenshots |
| 10 | Every tray menu item works | BLOCKED | Checklist and log |
| 11 | Pause monitoring stops polling | BLOCKED | Network/monitor trace |
| 12 | Native notifications appear | BLOCKED | Screenshot |
| 13 | Notification opens the correct PR/run | BLOCKED | Screen recording and target URL/run ID |
| 14 | User-enabled autostart works after sign-in | BLOCKED | Settings and post-login screenshot |
| 15 | Repeated launch activates one instance | BLOCKED | Process list and screenshot |
| 16 | True quit terminates the Sidecar | BLOCKED | Before/after process list |
| 17 | Uninstaller completes | BLOCKED | Uninstaller log |
| 18 | No background process remains after uninstall | BLOCKED | Process list |
| 19 | Windows paths handle spaces and non-ASCII text | BLOCKED | Test path and run log |
| 20 | Logs/database use the expected AppData directory | BLOCKED | Paths and redacted directory listing |

## Test record template

```text
Tester:
Date/time/timezone:
Windows edition/build:
Architecture:
Artifact filename:
Artifact SHA256:
Git commit:
Install mode (fresh/upgrade):

Check #:
Result (PASS/FAIL/BLOCKED):
Observed behaviour:
Evidence path/link:
Redacted log path:
Issue link:
```

Only a completed record from a real Windows graphical environment may advance
an item to `VERIFIED_WINDOWS_MANUAL`. A Windows runner result remains
`VERIFIED_WINDOWS_CI`.
