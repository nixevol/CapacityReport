# Build Notes

Use the root scripts for release builds:

```powershell
scripts\build.bat server
scripts\build.bat docker
scripts\build.bat desktop
```

On Linux or macOS:

```bash
sh scripts/build.sh server
sh scripts/build.sh docker
sh scripts/build.sh desktop
```

## Targets

- `server`: builds a portable server package for the current OS.
- `docker`: builds the Docker image and validates the compose file.
- `desktop`: builds a Tauri desktop package with the Python server sidecar.
- `all`: runs all targets.

Native server and desktop packages must be built on the target OS. Build Windows packages on Windows, Linux packages on Linux, and macOS packages on macOS. Docker images can be built from the Windows development host.
