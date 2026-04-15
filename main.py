"""Ponto de entrada da aplicação de visualização de câmera SciCam.

Responsabilidades deste módulo:
  1. Registrar as bibliotecas nativas do SDK no caminho de busca do sistema
     ANTES de qualquer import que dependa de ctypes (ex.: sci_camera.py).
  2. Configurar o sistema de logs.
  3. Criar a aplicação PyQt6 e exibir a janela principal.

Estratégia de libs nativas (Linux):
  O linker dinâmico (ld.so) não relê LD_LIBRARY_PATH após o processo iniciar.
  Por isso, se o diretório ainda não estiver na variável, o processo é
  reiniciado via os.execv com a variável corretamente definida.
"""
import sys
import os

# ---- Configuração de libs nativas (deve rodar ANTES de qualquer import ctypes) ----
_platform_dir = 'windows' if sys.platform == 'win32' else 'linux'
_libs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs', _platform_dir)
if os.path.isdir(_libs_dir):
    if sys.platform == 'win32':
        # No Windows, registra o diretório como fonte adicional de DLLs
        os.add_dll_directory(_libs_dir)
    elif _libs_dir not in os.environ.get('LD_LIBRARY_PATH', '').split(':'):
        # No Linux, reinicia o processo com LD_LIBRARY_PATH atualizado
        os.environ['LD_LIBRARY_PATH'] = _libs_dir + ':' + os.environ.get('LD_LIBRARY_PATH', '')
        os.execv(sys.executable, [sys.executable] + sys.argv)

import signal

from app.infrastructure.logging.log_setup import setup_logging
log = setup_logging()

from PyQt6.QtWidgets import QApplication
from app.presentation.main_window import MainWindow

if __name__ == "__main__":
    log.info('=== Iniciando aplicação ===')
    app = QApplication(sys.argv)

    # Ignora SIGINT para evitar KeyboardInterrupt dentro de slots Qt.
    # O debugpy envia SIGINT durante a inicialização do debug session no VS Code,
    # o que sem esse handler causaria encerramento inesperado do app.
    # O fechamento correto é feito pelo closeEvent da janela principal.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    window = MainWindow()
    window.setMinimumSize(800, 600)
    window.show()
    # Centraliza a janela na tela principal
    screen = app.primaryScreen().availableGeometry()
    window.move(screen.center() - window.rect().center())
    exit_code = app.exec()
    log.info('=== Aplicação encerrada (código %d) ===', exit_code)
    sys.exit(exit_code)

