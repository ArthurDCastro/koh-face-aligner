
#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "=== KOH - Instalando dependências ==="

# Criar ambiente virtual, caso não exista
if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv .venv
fi

# Ativar ambiente virtual
source .venv/bin/activate

# Atualizar pip
python -m pip install --upgrade pip

# Instalar dependências
echo "Instalando requirements.txt..."
python -m pip install -r requirements.txt

echo "=== Instalação concluída! ==="
echo "Para ativar o ambiente:"
echo "source .venv/bin/activate"
