#!/usr/bin/env python3
"""
Kubernetes utilities for PTP MCP Server

Provides utilities for handling kubeconfig files, including support for
base64-encoded kubeconfig content passed as parameters to target different clusters.
"""

import base64
import logging
import os
import tempfile
from contextlib import contextmanager
from typing import List, Optional, Generator

logger = logging.getLogger(__name__)


@contextmanager
def kubeconfig_from_base64(kubeconfig_b64: str = None) -> Generator[Optional[str], None, None]:
    """
    Context manager to create a temporary kubeconfig file from base64-encoded content.

    If kubeconfig_b64 is None or empty, yields None (use default kubeconfig).
    Otherwise, decodes the base64 content, writes to a temp file, and yields the path.
    The temp file is automatically cleaned up when the context exits.

    Args:
        kubeconfig_b64: Base64-encoded kubeconfig file content (optional).
                        Encode with: cat kubeconfig | base64 -w0

    Yields:
        Path to temporary kubeconfig file, or None if using default

    Example:
        with kubeconfig_from_base64(kubeconfig_b64) as kubeconfig_path:
            cmd = build_oc_command(kubeconfig_path)
            cmd.extend(["get", "pods"])
            subprocess.run(cmd, ...)
    """
    if not kubeconfig_b64:
        yield None
        return

    # Reject oversized input (kubeconfigs are typically a few KB)
    MAX_KUBECONFIG_SIZE = 1024 * 1024  # 1MB
    if len(kubeconfig_b64) > MAX_KUBECONFIG_SIZE:
        raise ValueError(f"Kubeconfig input too large ({len(kubeconfig_b64)} bytes, max {MAX_KUBECONFIG_SIZE})")

    temp_path = None
    try:
        # Strip any whitespace (spaces, newlines, tabs) that LLMs may insert
        # when formatting long base64 strings
        cleaned_b64 = ''.join(kubeconfig_b64.split())

        # Decode base64 content
        kubeconfig_content = base64.b64decode(cleaned_b64).decode('utf-8')

        # Basic validation that this looks like a kubeconfig
        if 'apiVersion' not in kubeconfig_content or 'clusters' not in kubeconfig_content:
            raise ValueError("Decoded content does not appear to be a valid kubeconfig")

        # Write to temporary file (NamedTemporaryFile creates with 0o600 by default)
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.kubeconfig',
            delete=False,
            prefix='ptp-mcp-'
        ) as f:
            f.write(kubeconfig_content)
            temp_path = f.name

        logger.debug(f"Created temporary kubeconfig at {temp_path}")
        yield temp_path

    except base64.binascii.Error as e:
        logger.error(f"Failed to decode base64 kubeconfig: {e}")
        raise ValueError(f"Invalid base64-encoded kubeconfig: {e}")
    except Exception as e:
        logger.error(f"Error creating temporary kubeconfig: {e}")
        raise
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.debug(f"Cleaned up temporary kubeconfig at {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary kubeconfig: {e}")


def build_oc_command(kubeconfig_path: str = None) -> List[str]:
    """
    Build base oc command with optional kubeconfig.

    Args:
        kubeconfig_path: Path to kubeconfig file (optional)

    Returns:
        List starting with ["oc"] or ["oc", "--kubeconfig", path]

    Example:
        cmd = build_oc_command(kubeconfig_path)
        cmd.extend(["get", "ptpconfig", "-n", namespace, "-o", "yaml"])
        result = subprocess.run(cmd, ...)
    """
    cmd = ["oc"]
    if kubeconfig_path:
        cmd.extend(["--kubeconfig", kubeconfig_path])
    return cmd
