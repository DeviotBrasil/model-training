#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$SCRIPT_DIR/libs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# Buffer UDP mínimo para GigE Vision (evita frames incompletos por overflow de socket)
# rmem_max padrão do Linux (~200KB) é insuficiente para streams de imagem de alta resolução
sudo sysctl -w net.core.rmem_max=26214400 net.core.rmem_default=26214400 2>/dev/null || \
    echo "Aviso: não foi possível aumentar rmem — rode 'sudo sysctl -w net.core.rmem_max=26214400' manualmente se imagens ficarem incompletas"

exec python3 "$SCRIPT_DIR/main.py" "$@"
