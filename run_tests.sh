#!/bin/bash
# Script para ejecutar tests con pytest
# Uso: ./run_tests.sh [filtro_opcional]
# Ej: ./run_tests.sh test_generation_service

cd "$(dirname "$0")"

if [ -z "$1" ]; then
    echo "Ejecutando todos los tests..."
    python -m pytest src/tests -v --tb=short
else
    echo "Ejecutando tests que coincidan con: $1"
    python -m pytest src/tests -k "$1" -v --tb=short
fi
