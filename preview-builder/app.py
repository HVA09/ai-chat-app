"""Isolated JavaScript preview builder.

The HTTP service is separate from the main backend. It accepts validated source,
installs dependencies without lifecycle scripts, and runs npm build only inside
an explicit bubblewrap sandbox with a network-disabled child process.
"""
from __future__ import annotations

import asyncio
import base64
import hmac
import os
import signal
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field


MAX_FILES = int(os.getenv("BUILDER_MAX_FILES", "200"))
MAX_TOTAL_CHARS = int(os.getenv("BUILDER_MAX_TOTAL_CHARS", "450000"))
MAX_FILE_BYTES = int(os.getenv("BUILDER_MAX_FILE_BYTES", "10485760"))
MAX_ARTIFACT_BYTES = int(os.getenv("BUILDER_MAX_ARTIFACT_BYTES", "10485760"))
MAX_BUILD_SECONDS = float(os.getenv("BUILDER_MAX_BUILD_SECONDS", "120"))
ENABLE_BUILDS = os.getenv("BUILDER_ENABLE_BUILDS", "false").strip().lower() == "true"
SANDBOX_BIN = os.getenv("BUILDER_SANDBOX_BIN", "bwrap")
BUILDER_TOKEN = os.getenv("BUILDER_TOKEN", "")

SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
SECRET_NAMES = {".env", ".env.local", ".env.production", ".env.development"}

app = FastAPI(title="AI Project Preview Builder", version="1")


class BuildFile(BaseModel):
    path: str = Field(min_length=1, max_length=512)
    content: str


class BuildRequest(BaseModel):
    project_id: int
    project_kind: str
    files: list[BuildFile]
    build_command: str = "npm run build"


class BuildResponse(BaseModel):
    entrypoint: str
    artifact_base64: str


def _normalize_and_validate(files: list[BuildFile]) -> list[BuildFile]:
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=413, detail="Too many files.")

    total_chars = 0
    seen: set[str] = set()
    normalized: list[BuildFile] = []

    for item in files:
        path = item.path.replace("\\", "/").strip()
        parts = path.split("/")
        if not path or path.startswith("/") or any(part == ".." for part in parts):
            raise HTTPException(status_code=400, detail="Unsafe file path.")
        if any(part == "" for part in parts):
            raise HTTPException(status_code=400, detail="Unsafe file path.")
        lower = path.lower()
        name = Path(path).name.lower()
        if name in SECRET_NAMES or lower.endswith(SECRET_SUFFIXES):
            raise HTTPException(status_code=400, detail="Secret or private-key file is not allowed.")
        if "\x00" in item.content:
            raise HTTPException(status_code=400, detail="Binary content is not allowed.")
        encoded_size = len(item.content.encode("utf-8"))
        if encoded_size > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="File is too large.")
        if path in seen:
            raise HTTPException(status_code=400, detail="Duplicate path.")
        seen.add(path)
        total_chars += len(item.content)
        if total_chars > MAX_TOTAL_CHARS:
            raise HTTPException(status_code=413, detail="Project content is too large.")
        normalized.append(BuildFile(path=path, content=item.content))

    if not any(item.path.lower() == "package.json" for item in normalized):
        raise HTTPException(status_code=400, detail="package.json is required.")
    return normalized


def _sandbox_command(workdir: Path) -> list[str]:
    return [
        SANDBOX_BIN,
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--clearenv",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/usr/local", "/usr/local",
        "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64",
        "--ro-bind", "/etc/ssl", "/etc/ssl",
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--bind", str(workdir), "/workspace",
        "--chdir", "/workspace",
        "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
        "--setenv", "HOME", "/tmp",
        "--setenv", "NODE_ENV", "production",
        "--",
        "/usr/local/bin/npm",
        "run",
        "build",
    ]


async def _run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: float,
) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
        env={
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false",
            "NPM_CONFIG_AUDIT": "false",
            "NPM_CONFIG_FUND": "false",
        },
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        os.killpg(process.pid, signal.SIGKILL)
        await process.communicate()
        raise HTTPException(status_code=408, detail="Preview build timed out.")
    return process.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode(
        "utf-8", errors="replace"
    )


def _find_artifact(workdir: Path) -> tuple[Path, str]:
    candidates = [
        (workdir / "dist", "index.html"),
        (workdir / "build", "index.html"),
        (workdir, "index.html"),
    ]
    for root, entrypoint in candidates:
        index = root / "index.html"
        if index.is_file():
            return root, entrypoint
    raise HTTPException(status_code=422, detail="No supported static artifact was produced.")


def _zip_artifact(root: Path) -> bytes:
    root_resolved = root.resolve()
    total_bytes = 0
    files_count = 0
    buffer = tempfile.SpooledTemporaryFile(max_size=MAX_ARTIFACT_BYTES)
    try:
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_dir():
                    continue
                if path.is_symlink():
                    raise HTTPException(status_code=422, detail="Symlinks are not allowed in artifacts.")
                resolved = path.resolve()
                if root_resolved != resolved and root_resolved not in resolved.parents:
                    raise HTTPException(status_code=422, detail="Artifact escapes its build root.")
                size = path.stat().st_size
                total_bytes += size
                files_count += 1
                if total_bytes > MAX_ARTIFACT_BYTES:
                    raise HTTPException(status_code=413, detail="Artifact is too large.")
                if files_count > MAX_FILES:
                    raise HTTPException(status_code=413, detail="Artifact contains too many files.")
                archive.write(path, path.relative_to(root))
        buffer.seek(0)
        data = buffer.read()
        if len(data) > MAX_ARTIFACT_BYTES:
            raise HTTPException(status_code=413, detail="Compressed artifact is too large.")
        return data
    finally:
        buffer.close()


def _authorized(authorization: str | None) -> bool:
    if not BUILDER_TOKEN or not authorization:
        return False
    scheme, _, token = authorization.partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(token, BUILDER_TOKEN)


@app.get("/")
async def root():
    return {"status": "ok", "enabled": ENABLE_BUILDS}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "enabled": ENABLE_BUILDS}


@app.post("/v1/build", response_model=BuildResponse)
async def build_preview(
    payload: BuildRequest,
    authorization: str | None = Header(default=None),
    x_preview_protocol: str | None = Header(default=None),
):
    if not _authorized(authorization):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")
    if x_preview_protocol != "1":
        raise HTTPException(status_code=400, detail="Unsupported preview protocol.")
    if payload.project_kind != "javascript":
        raise HTTPException(status_code=400, detail="Only JavaScript projects are supported.")
    if payload.build_command != "npm run build":
        raise HTTPException(status_code=400, detail="Unsupported build command.")
    if not ENABLE_BUILDS:
        raise HTTPException(status_code=503, detail="Preview builds are disabled.")

    if shutil.which(SANDBOX_BIN) is None:
        raise HTTPException(status_code=503, detail="Required sandbox runtime is unavailable.")

    files = _normalize_and_validate(payload.files)

    with tempfile.TemporaryDirectory(prefix="preview-build-") as temp_dir:
        workdir = Path(temp_dir)
        for item in files:
            destination = workdir / item.path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(item.content, encoding="utf-8")

        lockfile_exists = (workdir / "package-lock.json").is_file()
        install_command = [
            "/usr/local/bin/npm",
            "ci" if lockfile_exists else "install",
            "--ignore-scripts",
            "--audit=false",
            "--fund=false",
            "--no-update-notifier",
        ]
        if not lockfile_exists:
            install_command.append("--package-lock=false")

        install_code, install_out, install_err = await _run_command(
            install_command,
            cwd=workdir,
            timeout=MAX_BUILD_SECONDS,
        )
        if install_code != 0:
            detail = (install_err or install_out)[-3000:]
            raise HTTPException(status_code=422, detail=f"Dependency install failed: {detail}")

        build_code, build_out, build_err = await _run_command(
            _sandbox_command(workdir),
            timeout=MAX_BUILD_SECONDS,
        )
        if build_code != 0:
            detail = (build_err or build_out)[-3000:]
            raise HTTPException(status_code=422, detail=f"Preview build failed: {detail}")

        artifact_root, entrypoint = _find_artifact(workdir)
        artifact = _zip_artifact(artifact_root)
        return BuildResponse(
            entrypoint=entrypoint,
            artifact_base64=base64.b64encode(artifact).decode("ascii"),
            artifact_size_bytes=len(artifact),
        )
