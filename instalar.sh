#!/bin/bash
# Script para instalar el backend

echo "╔═══════════════════════════════════════════════════════╗"
echo "║      Instalación del Backend - Portal USEBEQ         ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Verificar si estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Debes ejecutar este script desde el directorio backend/"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
    echo "✅ Entorno virtual creado"
else
    echo "✅ Entorno virtual ya existe"
fi

echo ""

# Activar entorno virtual e instalar dependencias
echo "📥 Instalando dependencias..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencias instaladas correctamente"
else
    echo "❌ Error al instalar dependencias"
    exit 1
fi

echo ""

# Verificar archivo .env
if [ -f ".env" ]; then
    echo "✅ Archivo .env configurado"
else
    echo "⚠️  Archivo .env no encontrado"
    echo "   Copiando desde .env.example..."
    cp .env.example .env
    echo "   Por favor edita .env con tus credenciales"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║        ✅ Backend instalado correctamente             ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Para iniciar el servidor:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
