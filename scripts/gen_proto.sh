#!/usr/bin/env bash
# Regenerate the gRPC protobuf stubs from proto/racehooks/v1/feed.proto.
#
# Generated files are committed under racehooks/grpc/_gen (the Python norm),
# hidden behind the hand-written client in racehooks/grpc/client.py.
#
# Requires the codegen toolchain:  pip install -e '.[codegen]'
# (grpcio-tools + protoletariat). protoletariat rewrites the absolute imports
# grpcio-tools emits into package-relative ones via its descriptor-set ("raw")
# mode, so no standalone `protoc` binary is needed.
set -euo pipefail

cd "$(dirname "$0")/.."

OUT=racehooks/grpc/_gen
DESC="$(mktemp -t feed_desc.XXXXXX.pb)"
trap 'rm -f "$DESC"' EXIT

rm -rf "$OUT"
mkdir -p "$OUT"

python -m grpc_tools.protoc \
  --proto_path=proto \
  --python_out="$OUT" \
  --grpc_python_out="$OUT" \
  --pyi_out="$OUT" \
  --include_imports \
  --descriptor_set_out="$DESC" \
  proto/racehooks/v1/feed.proto

# Rewrite absolute imports to package-relative + add __init__.py at each level.
protol --create-package --in-place --python-out "$OUT" raw "$DESC"

echo "Generated stubs in $OUT"
