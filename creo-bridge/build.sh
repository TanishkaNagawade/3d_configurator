#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/build"
mkdir -p "$OUT"
SOURCES=$(find "$ROOT/src" -name "*.java")

if ! command -v javac >/dev/null 2>&1; then
  echo "error: javac not found — install a JDK (JAVA_HOME) to build the bridge" >&2
  exit 1
fi
javac -d "$OUT/classes" $(find "$ROOT/src" -name "*.java")
cat > "$OUT/MANIFEST.mf" <<EOF
Manifest-Version: 1.0
Main-Class: org.ecpd.bridge.Bridge
EOF
jar cfm "$OUT/creo-bridge.jar" "$OUT/MANIFEST.mf" -C "$OUT/classes" .
echo "built $OUT/creo-bridge.jar"
