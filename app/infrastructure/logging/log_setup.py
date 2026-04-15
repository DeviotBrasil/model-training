"""Configuração centralizada do sistema de logs da aplicação.

Inicializa dois handlers:
  - Arquivo rotativo (logs/app.log): nível DEBUG, máximo 5 MB, até 5 backups.
  - Console (stdout): nível INFO.

Deve ser chamado uma única vez em main.py, antes de qualquer outro import que use logging.
"""
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Tamanho máximo de cada arquivo de log antes da rotação (5 MB)
LOG_MAX_BYTES = 5 * 1024 * 1024
# Número de arquivos de backup mantidos após a rotação
LOG_BACKUP_COUNT = 5


def setup_logging(log_dir: str | None = None) -> logging.Logger:
    """Configura e retorna o logger raiz da aplicação ('scicam').

    Args:
        log_dir: Diretório onde o arquivo app.log será criado.
                 Se omitido, usa a pasta logs/ na raiz do projeto.

    Returns:
        Logger configurado com o nome 'scicam'.
    """
    if log_dir is None:
        log_dir = str(Path(__file__).parents[3] / 'logs')

    os.makedirs(log_dir, exist_ok=True)  # Cria o diretório de logs se ainda não existir

    formatter = logging.Formatter(
        fmt='%(asctime)s  %(levelname)-8s  %(name)s  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Handler de arquivo rotativo: grava tudo (DEBUG+) para facilitar diagnóstico
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8',
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Handler de console: exibe apenas INFO+ para não poluir o terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logging.root.setLevel(logging.DEBUG)
    logging.root.addHandler(file_handler)
    logging.root.addHandler(console_handler)

    return logging.getLogger('scicam')
