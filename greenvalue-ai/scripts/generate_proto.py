#!/usr/bin/env python3
"""Generate Python gRPC stubs from ai_service.proto."""
import subprocess
import sys
from pathlib import Path

PROTO_DIR = Path(__file__).parent.parent / "protos"
PROTO_FILE = PROTO_DIR / "greenvalue" / "v1" / "ai_service.proto"
OUT_DIR = Path(__file__).parent.parent / "modules" / "grpc_server" / "generated"

OUT_DIR.mkdir(parents=True, exist_ok=True)
# Create __init__.py for the generated package
(OUT_DIR / "__init__.py").touch()

cmd = [
    sys.executable, "-m", "grpc_tools.protoc",
    f"--proto_path={PROTO_DIR}",
    f"--python_out={OUT_DIR}",
    f"--grpc_python_out={OUT_DIR}",
    f"--pyi_out={OUT_DIR}",
    str(PROTO_FILE),
]

print(f"Running: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print(f"Error: {result.stderr}")
    sys.exit(1)

print(f"Generated stubs in {OUT_DIR}")
print(result.stdout)
