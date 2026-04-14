import sys
import os

# ---- Configuração de libs nativas (deve rodar ANTES de qualquer import ctypes) ----
_libs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs')
if os.path.isdir(_libs_dir):
    if sys.platform == 'win32':
        os.add_dll_directory(_libs_dir)
    elif _libs_dir not in os.environ.get('LD_LIBRARY_PATH', '').split(':'):
        os.environ['LD_LIBRARY_PATH'] = _libs_dir + ':' + os.environ.get('LD_LIBRARY_PATH', '')
        os.execv(sys.executable, [sys.executable] + sys.argv)

from app.infrastructure.logging.log_setup import setup_logging
log = setup_logging()

from PyQt6.QtWidgets import QApplication
from app.presentation.main_window import MainWindow

if __name__ == "__main__":
    log.info('=== Iniciando aplicação ===')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setMinimumSize(800, 600)
    window.show()
    screen = app.primaryScreen().availableGeometry()
    window.move(screen.center() - window.rect().center())
    exit_code = app.exec()
    log.info('=== Aplicação encerrada (código %d) ===', exit_code)
    sys.exit(exit_code)

