"""
Skill dependency installation.

Installs skill dependencies based on install specs.
"""
from __future__ import annotations

import asyncio
import logging
import platform
import shutil
import tempfile
import tarfile
import zipfile
from pathlib import Path
from typing import Any
import aiohttp

from .types import Skill, SkillInstallSpec

logger = logging.getLogger(__name__)


async def install_skill_dependencies(
    skill: Skill,
    install_specs: list[SkillInstallSpec] | None = None
) -> tuple[bool, list[str]]:
    """
    Install skill dependencies based on install specs.
    
    Supported install kinds:
    - brew: brew install <formula>
    - node: npm install -g <package>
    - go: go install <module>
    - uv: uv pip install <package>
    - download: Download and extract from URL
    
    Args:
        skill: Skill to install dependencies for
        install_specs: Install specifications (uses skill.metadata.install if None)
        
    Returns:
        Tuple of (success, errors)
    """
    if install_specs is None:
        if skill.metadata and skill.metadata.install:
            install_specs = skill.metadata.install
        else:
            return (True, [])  # No dependencies to install
    
    errors = []
    current_platform = _get_platform()
    
    for spec in install_specs:
        # Check OS requirement
        if spec.os and current_platform not in spec.os:
            logger.debug(f"Skipping install spec (wrong OS): {spec.id or spec.kind}")
            continue
        
        try:
            await _install_spec(spec)
            logger.info(f"Installed {spec.kind}: {spec.id or spec.formula or spec.package or spec.module or spec.url}")
        except Exception as e:
            error_msg = f"Failed to install {spec.kind} {spec.id or ''}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    return (len(errors) == 0, errors)


async def _install_spec(spec: SkillInstallSpec) -> None:
    """Install a single spec"""
    if spec.kind == "brew":
        await _install_brew(spec)
    elif spec.kind == "node":
        await _install_node(spec)
    elif spec.kind == "go":
        await _install_go(spec)
    elif spec.kind == "uv":
        await _install_uv(spec)
    elif spec.kind == "download":
        await _install_download(spec)
    else:
        raise ValueError(f"Unknown install kind: {spec.kind}")


async def _install_brew(spec: SkillInstallSpec) -> None:
    """Install via Homebrew"""
    if not spec.formula:
        raise ValueError("brew install requires 'formula'")
    
    # Check if already installed
    check_proc = await asyncio.create_subprocess_exec(
        "brew", "list", spec.formula,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await check_proc.wait()
    
    if check_proc.returncode == 0:
        logger.debug(f"Brew formula {spec.formula} already installed")
        return
    
    # Install
    proc = await asyncio.create_subprocess_exec(
        "brew", "install", spec.formula,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        raise RuntimeError(f"brew install failed: {stderr.decode()}")


async def _install_node(spec: SkillInstallSpec) -> None:
    """Install via npm"""
    if not spec.package:
        raise ValueError("node install requires 'package'")
    
    # Check if already installed
    check_proc = await asyncio.create_subprocess_exec(
        "npm", "list", "-g", spec.package,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await check_proc.wait()
    
    if check_proc.returncode == 0:
        logger.debug(f"npm package {spec.package} already installed")
        return
    
    # Install
    proc = await asyncio.create_subprocess_exec(
        "npm", "install", "-g", spec.package,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        raise RuntimeError(f"npm install failed: {stderr.decode()}")


async def _install_go(spec: SkillInstallSpec) -> None:
    """Install via go install"""
    if not spec.module:
        raise ValueError("go install requires 'module'")
    
    proc = await asyncio.create_subprocess_exec(
        "go", "install", spec.module,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        raise RuntimeError(f"go install failed: {stderr.decode()}")


async def _install_uv(spec: SkillInstallSpec) -> None:
    """Install via uv pip"""
    if not spec.package:
        raise ValueError("uv install requires 'package'")
    
    proc = await asyncio.create_subprocess_exec(
        "uv", "pip", "install", spec.package,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        raise RuntimeError(f"uv pip install failed: {stderr.decode()}")


async def _install_download(spec: SkillInstallSpec) -> None:
    """Download and extract from URL"""
    if not spec.url:
        raise ValueError("download install requires 'url'")
    
    if not spec.target_dir:
        raise ValueError("download install requires 'target_dir'")
    
    target_path = Path(spec.target_dir).expanduser()
    target_path.mkdir(parents=True, exist_ok=True)
    
    # Download to temp file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        filename = spec.url.split('/')[-1]
        download_path = temp_path / filename
        
        # Download
        async with aiohttp.ClientSession() as session:
            async with session.get(spec.url) as response:
                response.raise_for_status()
                content = await response.read()
                download_path.write_bytes(content)
        
        # Extract if needed
        if spec.extract:
            if filename.endswith('.tar.gz') or filename.endswith('.tgz'):
                with tarfile.open(download_path, 'r:gz') as tar:
                    # Extract with strip_components
                    _extract_tar_strip(tar, target_path, spec.strip_components)
            elif filename.endswith('.zip'):
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    # Extract with strip_components
                    _extract_zip_strip(zip_ref, target_path, spec.strip_components)
            else:
                raise ValueError(f"Unsupported archive format: {filename}")
        else:
            # Just copy the file
            shutil.copy(download_path, target_path / filename)
    
    logger.info(f"Downloaded and extracted to {target_path}")


def _extract_tar_strip(tar: tarfile.TarFile, target: Path, strip: int) -> None:
    """Extract tar with strip components"""
    for member in tar.getmembers():
        # Strip leading components
        parts = member.name.split('/')
        if len(parts) <= strip:
            continue
        
        new_name = '/'.join(parts[strip:])
        member.name = new_name
        tar.extract(member, target)


def _extract_zip_strip(zip_ref: zipfile.ZipFile, target: Path, strip: int) -> None:
    """Extract zip with strip components"""
    for member in zip_ref.namelist():
        # Strip leading components
        parts = member.split('/')
        if len(parts) <= strip:
            continue
        
        new_name = '/'.join(parts[strip:])
        target_path = target / new_name
        
        if member.endswith('/'):
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zip_ref.open(member) as source:
                target_path.write_bytes(source.read())


def _get_platform() -> str:
    """Get current platform name"""
    system = platform.system().lower()
    if system == 'darwin':
        return 'darwin'
    elif system == 'linux':
        return 'linux'
    elif system == 'windows':
        return 'win32'
    return system


__all__ = [
    "install_skill_dependencies",
]
