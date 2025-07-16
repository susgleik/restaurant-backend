#!/bin/bash

# Script de construcción personalizado para Render
echo "🔧 Iniciando construcción personalizada para Restaurant API..."

# Actualizar pip y herramientas de construcción
echo "📦 Actualizando pip y herramientas..."
pip install --upgrade pip setuptools wheel

# Instalar dependencias de compilación para pydantic-core
echo "🛠️ Instalando dependencias de compilación..."
pip install setuptools-rust

# Configurar variables de entorno para Rust
export CARGO_NET_GIT_FETCH_WITH_CLI=true
export CARGO_HOME=/tmp/cargo
export RUSTUP_HOME=/tmp/rustup

# Instalar Rust si no está disponible
if ! command -v rustc &> /dev/null; then
    echo "🦀 Instalando Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
fi

# Instalar pydantic-core con opciones específicas
echo "⚙️ Instalando pydantic-core..."
pip install pydantic-core==2.10.1 --no-cache-dir --verbose

# Instalar el resto de dependencias
echo "📚 Instalando dependencias restantes..."
pip install -r requirements.txt --no-cache-dir

# Configurar estructura de carpetas
echo "📁 Configurando estructura de carpetas..."
python setup_uploads.py

# Verificar instalación
echo "🔍 Verificando instalación..."
python -c "import fastapi; import pydantic; print('✅ FastAPI y Pydantic instalados correctamente')"

echo "✅ Construcción completada exitosamente!"