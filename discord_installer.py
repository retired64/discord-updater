#!/usr/bin/env python3
"""
Discord Installer Pro - Versión de Producción
==============================================
Instalador gráfico profesional para Discord en sistemas Linux.
Soporta instalación, actualización y gestión de versiones.

Autor: Retired64
Versión: 3.0.0
Licencia: MIT
"""

import sys
import os
import subprocess
import tempfile
import shlex
import logging
import tarfile
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QProgressBar, QTextEdit
)
from PySide6.QtCore import Qt, QProcess, Signal, QObject, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor


# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

class Config:
    """Configuración centralizada de la aplicación"""
    APP_VERSION = "3.0.0"
    APP_NAME = "Discord Installer"
    INSTALL_DIR = "/opt/discord"
    DESKTOP_FILE_DIR = "/usr/share/applications"
    BIN_SYMLINK = "/usr/local/bin/discord"
    LOG_FILE = Path.home() / ".discord_installer.log"
    
    # Rutas alternativas de instalación (fallback)
    ALT_INSTALL_DIR = "/usr/share/discord"
    
    # Patrones de búsqueda
    DISCORD_PATTERN = "discord-*.tar.gz"
    
    # Timeouts
    PROCESS_TIMEOUT = 300000  # 5 minutos en ms


# ============================================================================
# SISTEMA DE LOGGING
# ============================================================================

def setup_logging():
    """Configura el sistema de logging con rotación de archivos"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# ============================================================================
# UTILIDADES DEL SISTEMA
# ============================================================================

class SystemUtils:
    """Utilidades para interactuar con el sistema operativo"""
    
    @staticmethod
    def get_download_dir() -> Path:
        """Obtiene el directorio de descargas del usuario de forma universal"""
        try:
            # Método 1: xdg-user-dir (estándar XDG)
            result = subprocess.run(
                ['xdg-user-dir', 'DOWNLOAD'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                download_path = Path(result.stdout.strip())
                if download_path.exists():
                    logger.info(f"Directorio de descargas detectado: {download_path}")
                    return download_path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("xdg-user-dir no disponible, usando fallbacks")
        
        # Método 2: Nombres comunes en español e inglés
        home = Path.home()
        for dirname in ['Descargas', 'Downloads', 'descargas', 'downloads']:
            path = home / dirname
            if path.exists():
                logger.info(f"Directorio de descargas encontrado: {path}")
                return path
        
        # Fallback final: home
        logger.warning(f"No se encontró carpeta de descargas, usando: {home}")
        return home
    
    @staticmethod
    def validate_tar_file(tar_path: str) -> bool:
        """Valida que un archivo tar.gz sea válido y no esté corrupto"""
        try:
            with tarfile.open(tar_path, 'r:gz') as tar:
                # Intentar listar contenidos
                members = tar.getmembers()
                if len(members) == 0:
                    logger.error(f"Archivo tar vacío: {tar_path}")
                    return False
                logger.info(f"Archivo tar válido con {len(members)} elementos")
                return True
        except Exception as e:
            logger.error(f"Error validando archivo tar: {e}")
            return False
    
    @staticmethod
    def get_file_hash(filepath: str) -> str:
        """Calcula el hash SHA256 de un archivo"""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculando hash: {e}")
            return ""
    
    @staticmethod
    def check_root_access() -> bool:
        """Verifica si pkexec está disponible"""
        try:
            result = subprocess.run(
                ['which', 'pkexec'],
                capture_output=True,
                timeout=5
            )
            available = result.returncode == 0
            logger.info(f"pkexec disponible: {available}")
            return available
        except Exception as e:
            logger.error(f"Error verificando pkexec: {e}")
            return False
    
    @staticmethod
    def get_installed_version() -> Optional[str]:
        """Obtiene la versión de Discord instalada actualmente"""
        for install_path in [Config.INSTALL_DIR, Config.ALT_INSTALL_DIR]:
            version_file = Path(install_path) / "resources" / "build_info.json"
            if version_file.exists():
                try:
                    import json
                    with open(version_file, 'r') as f:
                        data = json.load(f)
                        version = data.get('version', 'Desconocida')
                        logger.info(f"Versión instalada detectada: {version}")
                        return version
                except Exception as e:
                    logger.warning(f"Error leyendo versión: {e}")
        
        # Fallback: verificar si el binario existe
        for install_path in [Config.INSTALL_DIR, Config.ALT_INSTALL_DIR]:
            if (Path(install_path) / "Discord").exists():
                logger.info("Discord instalado (versión desconocida)")
                return "Instalado"
        
        return None


# ============================================================================
# SCRIPT DE INSTALACIÓN BASH
# ============================================================================

INSTALL_SCRIPT_TEMPLATE = r"""#!/bin/bash
# Discord Installer Pro - Script de Instalación
# Generado automáticamente - No editar manualmente
# Versión: {version}
# Fecha: {date}

set -e  # Salir en caso de error
set -u  # Error en variables no definidas

# Variables
DISCORD_TAR={tar_path}
INSTALL_DIR={install_dir}
BACKUP_DIR="/tmp/discord_backup_$(date +%s)"
LOG_FILE="/tmp/discord_install_$(date +%s).log"

# Función de logging
log() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}}

# Función de limpieza en caso de error
cleanup_on_error() {{
    log "ERROR: La instalación falló. Limpiando..."
    if [ -d "$BACKUP_DIR" ] && [ -d "$INSTALL_DIR" ]; then
        log "Restaurando backup..."
        rm -rf "$INSTALL_DIR"
        mv "$BACKUP_DIR" "$INSTALL_DIR"
    fi
    exit 1
}}

trap cleanup_on_error ERR

log "=== Iniciando instalación de Discord ==="
log "Archivo: $DISCORD_TAR"
log "Destino: $INSTALL_DIR"

# 1. Validar archivo tar
log "Validando archivo tar..."
if [ ! -f "$DISCORD_TAR" ]; then
    log "ERROR: Archivo no encontrado: $DISCORD_TAR"
    exit 1
fi

if ! tar -tzf "$DISCORD_TAR" &>/dev/null; then
    log "ERROR: Archivo tar corrupto o inválido"
    exit 1
fi

# 2. Crear backup si existe instalación previa
if [ -d "$INSTALL_DIR" ]; then
    log "Creando backup de instalación existente..."
    cp -r "$INSTALL_DIR" "$BACKUP_DIR"
fi

# 3. Crear directorio temporal para extracción
TEMP_DIR=$(mktemp -d)
log "Extrayendo en: $TEMP_DIR"
tar -xzf "$DISCORD_TAR" -C "$TEMP_DIR"

# 4. Buscar carpeta Discord
DISCORD_FOLDER=$(find "$TEMP_DIR" -maxdepth 2 -type d -name "Discord" | head -n 1)

if [ -z "$DISCORD_FOLDER" ]; then
    log "ERROR: No se encontró la carpeta Discord en el archivo"
    rm -rf "$TEMP_DIR"
    exit 1
fi

log "Carpeta Discord encontrada: $DISCORD_FOLDER"

# 5. Remover instalación anterior
if [ -d "$INSTALL_DIR" ]; then
    log "Removiendo instalación anterior..."
    rm -rf "$INSTALL_DIR"
fi

# 6. Mover a directorio de instalación
log "Instalando Discord en $INSTALL_DIR..."
mkdir -p "$(dirname "$INSTALL_DIR")"
mv "$DISCORD_FOLDER" "$INSTALL_DIR"

# 7. Configurar permisos
log "Configurando permisos..."
chmod +x "$INSTALL_DIR/Discord"
chmod -R 755 "$INSTALL_DIR"

# 8. Crear archivo .desktop
log "Creando acceso directo..."
cat > "$INSTALL_DIR/discord.desktop" <<EOF
[Desktop Entry]
Name=Discord
StartupWMClass=discord
Comment=All-in-one voice and text chat for gamers
GenericName=Internet Messenger
Exec=$INSTALL_DIR/Discord
Icon=$INSTALL_DIR/discord.png
Type=Application
Categories=Network;InstantMessaging;
Path=$INSTALL_DIR
Terminal=false
StartupNotify=true
EOF

# 9. Instalar archivo .desktop
log "Instalando archivo .desktop..."
mkdir -p /usr/share/applications
cp "$INSTALL_DIR/discord.desktop" /usr/share/applications/discord.desktop
chmod 644 /usr/share/applications/discord.desktop

# 10. Crear enlace simbólico
log "Creando enlace simbólico..."
rm -f /usr/local/bin/discord
ln -s "$INSTALL_DIR/Discord" /usr/local/bin/discord

# 11. Actualizar base de datos de aplicaciones
log "Actualizando base de datos de aplicaciones..."
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# 12. Limpiar archivos temporales
log "Limpiando archivos temporales..."
rm -rf "$TEMP_DIR"
if [ -d "$BACKUP_DIR" ]; then
    log "Removiendo backup (instalación exitosa)..."
    rm -rf "$BACKUP_DIR"
fi

log "=== Instalación completada exitosamente ==="
log "Discord instalado en: $INSTALL_DIR"
log "Log guardado en: $LOG_FILE"

exit 0
"""


# ============================================================================
# INSTALADOR (LÓGICA DE NEGOCIO)
# ============================================================================

class DiscordInstaller(QObject):
    """Clase que maneja la lógica de instalación de Discord"""
    
    # Señales para comunicación con la UI
    progress_updated = Signal(int, str)
    installation_completed = Signal(bool, str)
    log_message = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.process = None
        self.tmp_script_path = None
        self.tar_file_path = None
        
    def find_discord_tar(self) -> Optional[Tuple[str, int]]:
        """
        Busca el archivo de Discord en Descargas
        Retorna: (ruta_completa, tamaño_en_bytes) o None
        """
        try:
            downloads = SystemUtils.get_download_dir()
            files = list(downloads.glob(Config.DISCORD_PATTERN))
            
            if not files:
                logger.info("No se encontraron archivos discord-*.tar.gz")
                return None
            
            # Ordenar por fecha de modificación (más nuevo primero)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            newest = files[0]
            size = newest.stat().st_size
            
            logger.info(f"Archivo encontrado: {newest} ({size} bytes)")
            return (str(newest), size)
            
        except Exception as e:
            logger.error(f"Error buscando archivo: {e}")
            return None
    
    def validate_installation_requirements(self) -> Tuple[bool, str]:
        """Valida que el sistema cumpla los requisitos"""
        
        # 1. Verificar pkexec
        if not SystemUtils.check_root_access():
            return False, "pkexec no está disponible. Instala policykit."
        
        # 2. Verificar espacio en disco
        try:
            stat = os.statvfs('/opt' if Path('/opt').exists() else '/usr')
            free_space = stat.f_bavail * stat.f_frsize
            required_space = 500 * 1024 * 1024  # 500 MB
            
            if free_space < required_space:
                return False, f"Espacio insuficiente. Se requieren 500 MB, disponibles: {free_space // (1024*1024)} MB"
        except Exception as e:
            logger.warning(f"No se pudo verificar espacio en disco: {e}")
        
        # 3. Verificar permisos de escritura (esto lo hará pkexec)
        
        return True, "Sistema compatible"
    
    def install(self, tar_path: str):
        """Inicia el proceso de instalación"""
        self.tar_file_path = tar_path
        
        try:
            self.log_message.emit("Validando archivo de instalación...")
            self.progress_updated.emit(10, "Validando archivo...")
            
            # Validar archivo tar
            if not SystemUtils.validate_tar_file(tar_path):
                raise Exception("El archivo tar.gz está corrupto o es inválido")
            
            self.log_message.emit("Archivo validado correctamente")
            self.progress_updated.emit(20, "Generando script de instalación...")
            
            # Calcular hash para logging
            file_hash = SystemUtils.get_file_hash(tar_path)
            logger.info(f"Hash del archivo: {file_hash}")
            
            # Generar script de instalación
            script_content = INSTALL_SCRIPT_TEMPLATE.format(
                version=Config.APP_VERSION,
                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                tar_path=shlex.quote(tar_path),
                install_dir=shlex.quote(Config.INSTALL_DIR)
            )
            
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(
                mode='w',
                delete=False,
                suffix='.sh',
                prefix='discord_install_'
            ) as tmp:
                tmp.write(script_content)
                self.tmp_script_path = tmp.name
            
            # Dar permisos de ejecución
            os.chmod(self.tmp_script_path, 0o755)
            logger.info(f"Script temporal creado: {self.tmp_script_path}")
            
            self.log_message.emit("Solicitando privilegios de administrador...")
            self.progress_updated.emit(30, "Esperando autorización...")
            
            # Ejecutar con pkexec
            self.process = QProcess()
            self.process.finished.connect(self._on_process_finished)
            self.process.readyReadStandardOutput.connect(self._on_stdout_ready)
            self.process.readyReadStandardError.connect(self._on_stderr_ready)
            
            # Timeout de seguridad
            QTimer.singleShot(Config.PROCESS_TIMEOUT, self._on_timeout)
            
            self.process.start("pkexec", [self.tmp_script_path])
            
            if not self.process.waitForStarted(5000):
                raise Exception("No se pudo iniciar el proceso de instalación")
            
            self.log_message.emit("Instalación en progreso...")
            self.progress_updated.emit(40, "Instalando Discord...")
            
        except Exception as e:
            logger.error(f"Error en instalación: {e}", exc_info=True)
            self._cleanup()
            self.installation_completed.emit(False, str(e))
    
    def _on_stdout_ready(self):
        """Procesa la salida estándar del proceso"""
        if self.process:
            output = bytes(self.process.readAllStandardOutput()).decode('utf-8')
            for line in output.strip().split('\n'):
                if line:
                    logger.info(f"STDOUT: {line}")
                    self.log_message.emit(line)
    
    def _on_stderr_ready(self):
        """Procesa la salida de error del proceso"""
        if self.process:
            output = bytes(self.process.readAllStandardError()).decode('utf-8')
            for line in output.strip().split('\n'):
                if line:
                    logger.warning(f"STDERR: {line}")
                    self.log_message.emit(f"⚠ {line}")
    
    def _on_process_finished(self, exit_code, exit_status):
        """Callback cuando termina el proceso de instalación"""
        logger.info(f"Proceso finalizado. Exit code: {exit_code}, Status: {exit_status}")
        
        self._cleanup()
        
        if exit_code == 0:
            self.progress_updated.emit(100, "¡Instalación completada!")
            self.installation_completed.emit(True, "Discord se instaló correctamente")
        elif exit_code == 126 or exit_code == 127:
            # Usuario canceló la autenticación
            self.progress_updated.emit(0, "Instalación cancelada")
            self.installation_completed.emit(False, "CANCELLED")
        else:
            error_msg = "La instalación falló. Verifica los logs para más detalles."
            self.progress_updated.emit(0, "Instalación fallida")
            self.installation_completed.emit(False, error_msg)
    
    def _on_timeout(self):
        """Maneja el timeout del proceso"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            logger.error("Timeout en instalación")
            self.process.kill()
            self._cleanup()
            self.installation_completed.emit(False, "Timeout: La instalación tomó demasiado tiempo")
    
    def _cleanup(self):
        """Limpia archivos temporales"""
        if self.tmp_script_path and os.path.exists(self.tmp_script_path):
            try:
                os.remove(self.tmp_script_path)
                logger.info(f"Script temporal eliminado: {self.tmp_script_path}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar script temporal: {e}")


# ============================================================================
# INTERFAZ GRÁFICA
# ============================================================================

class ModernButton(QPushButton):
    """Botón personalizado con efecto 3D"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(70)
        self.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._update_style()
    
    def _update_style(self):
        if self.isEnabled():
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #5865F2, stop:1 #4752C4);
                    color: white;
                    border-radius: 12px;
                    border: none;
                    border-bottom: 5px solid #3C45A5;
                    padding: 15px 30px;
                    margin-top: 0px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #4752C4, stop:1 #3C45A5);
                }
                QPushButton:pressed {
                    border-bottom: 0px;
                    margin-top: 5px;
                    background: #3C45A5;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: #40444B;
                    color: #72767D;
                    border-radius: 12px;
                    border: none;
                    border-bottom: 5px solid #2C2F33;
                    padding: 15px 30px;
                }
            """)
    
    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self._update_style()


class DiscordIcon(QLabel):
    """Widget personalizado para el icono de Discord"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.setScaledContents(False)
    
    def paintEvent(self, event):
        """Dibuja el icono de Discord"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fondo circular
        painter.setBrush(QColor("#5865F2"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(10, 10, 100, 100)
        
        # Logo simplificado (texto)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "D")


class DiscordInstallerUI(QMainWindow):
    """Interfaz gráfica principal del instalador"""
    
    def __init__(self):
        super().__init__()
        
        self.installer = DiscordInstaller()
        self.tar_file = None
        self.tar_size = 0
        self.installed_version = None
        
        self._setup_ui()
        self._connect_signals()
        
        # Iniciar búsqueda automática
        QTimer.singleShot(800, self._initial_scan)
    
    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        self.setWindowTitle(Config.APP_NAME)
        self.setFixedSize(550, 700)
        
        # Estilo global
        self.setStyleSheet("""
            QMainWindow {
                background-color: #23272A;
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
            }
            QTextEdit {
                background-color: #2C2F33;
                color: #DCDDDE;
                border: 1px solid #40444B;
                border-radius: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 8px;
            }
            QProgressBar {
                border: 2px solid #40444B;
                border-radius: 8px;
                text-align: center;
                background-color: #2C2F33;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #5865F2, stop:1 #7289DA);
                border-radius: 6px;
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        title = QLabel("DISCORD")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 36, QFont.Weight.ExtraBold))
        title.setStyleSheet("color: #5865F2; margin-bottom: 5px;")
        layout.addWidget(title)
        
        subtitle = QLabel("INSTALLER PRO")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 16, QFont.Weight.Light))
        subtitle.setStyleSheet("color: #B9BBBE; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Icono
        self.icon = DiscordIcon()
        icon_layout = QHBoxLayout()
        icon_layout.addStretch()
        icon_layout.addWidget(self.icon)
        icon_layout.addStretch()
        layout.addLayout(icon_layout)
        
        layout.addSpacing(10)
        
        # Estado del sistema
        self.system_status = QLabel("🔍 Escaneando sistema...")
        self.system_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.system_status.setFont(QFont("Segoe UI", 12))
        self.system_status.setStyleSheet("color: #B9BBBE; padding: 10px;")
        layout.addWidget(self.system_status)
        
        # Información de archivo
        self.file_info = QLabel("")
        self.file_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_info.setFont(QFont("Segoe UI", 11))
        self.file_info.setStyleSheet("color: #72767D;")
        self.file_info.setWordWrap(True)
        layout.addWidget(self.file_info)
        
        layout.addSpacing(10)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Botón principal
        self.install_button = ModernButton("BUSCANDO...")
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self._on_install_clicked)
        layout.addWidget(self.install_button)
        
        # Log de instalación (colapsable)
        log_label = QLabel("📋 Log de instalación:")
        log_label.setStyleSheet("color: #B9BBBE; font-size: 11px; margin-top: 10px;")
        layout.addWidget(log_label)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(120)
        self.log_view.setVisible(False)
        layout.addWidget(self.log_view)
        
        # Footer
        footer_layout = QHBoxLayout()
        
        version_label = QLabel(f"v{Config.APP_VERSION}")
        version_label.setStyleSheet("color: #40444B; font-size: 10px;")
        footer_layout.addWidget(version_label)
        
        footer_layout.addStretch()
        
        help_button = QPushButton("?")
        help_button.setFixedSize(25, 25)
        help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        help_button.setStyleSheet("""
            QPushButton {
                background-color: #40444B;
                color: #B9BBBE;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4752C4;
                color: white;
            }
        """)
        help_button.clicked.connect(self._show_help)
        footer_layout.addWidget(help_button)
        
        layout.addLayout(footer_layout)
    
    def _connect_signals(self):
        """Conecta las señales del instalador con la UI"""
        self.installer.progress_updated.connect(self._on_progress_updated)
        self.installer.installation_completed.connect(self._on_installation_completed)
        self.installer.log_message.connect(self._on_log_message)
    
    def _initial_scan(self):
        """Escaneo inicial del sistema"""
        try:
            # Verificar versión instalada
            self.installed_version = SystemUtils.get_installed_version()
            
            # Verificar requisitos
            compatible, msg = self.installer.validate_installation_requirements()
            if not compatible:
                self._show_error("Sistema no compatible", msg)
                self.install_button.setText("SISTEMA NO COMPATIBLE")
                return
            
            # Buscar archivo
            result = self.installer.find_discord_tar()
            
            if result:
                self.tar_file, self.tar_size = result
                filename = Path(self.tar_file).name
                size_mb = self.tar_size / (1024 * 1024)
                
                if self.installed_version:
                    action = "ACTUALIZAR"
                    status = f"✅ Discord {self.installed_version} detectado"
                else:
                    action = "INSTALAR"
                    status = "📦 Listo para instalar"
                
                self.system_status.setText(status)
                self.system_status.setStyleSheet("color: #57F287; font-weight: bold;")
                self.file_info.setText(f"{filename}\nTamaño: {size_mb:.1f} MB")
                self.install_button.setText(f"{action} DISCORD")
                self.install_button.setEnabled(True)
                
                logger.info(f"Instalación lista. Archivo: {filename}, Acción: {action}")
            else:
                self.system_status.setText("❌ Archivo no encontrado")
                self.system_status.setStyleSheet("color: #ED4245; font-weight: bold;")
                self.file_info.setText(
                    "Descarga discord-*.tar.gz desde\n"
                    "discord.com/download y colócalo en Descargas"
                )
                self.install_button.setText("ARCHIVO NO ENCONTRADO")
                logger.warning("No se encontró archivo de instalación")
                
        except Exception as e:
            logger.error(f"Error en escaneo inicial: {e}", exc_info=True)
            self._show_error("Error", f"Error al escanear el sistema:\n{e}")
    
    def _on_install_clicked(self):
        """Maneja el clic en el botón de instalación"""
        if not self.tar_file:
            return
        
        # Confirmar con el usuario
        action = "actualizar" if self.installed_version else "instalar"
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar instalación")
        msg.setText(f"¿Deseas {action} Discord?")
        msg.setInformativeText(
            f"Archivo: {Path(self.tar_file).name}\n"
            f"Destino: {Config.INSTALL_DIR}\n\n"
            "Se solicitarán privilegios de administrador."
        )
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            # Preparar UI para instalación
            self.install_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.log_view.setVisible(True)
            self.log_view.clear()
            
            # Iniciar instalación
            logger.info("Iniciando instalación por solicitud del usuario")
            self.installer.install(self.tar_file)
    
    def _on_progress_updated(self, value, message):
        """Actualiza la barra de progreso"""
        self.progress_bar.setValue(value)
        self.system_status.setText(message)
    
    def _on_log_message(self, message):
        """Añade mensaje al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(f"[{timestamp}] {message}")
    
    def _on_installation_completed(self, success, message):
        """Maneja la finalización de la instalación"""
        self.progress_bar.setVisible(False)
        
        if message == "CANCELLED":
            self.system_status.setText("Instalación cancelada por el usuario")
            self.system_status.setStyleSheet("color: #FAA61A;")
            self.install_button.setText("INSTALAR DISCORD")
            self.install_button.setEnabled(True)
            return
        
        if success:
            msg = QMessageBox(self)
            msg.setWindowTitle("¡Instalación completada!")
            msg.setText("✅ Discord se instaló correctamente")
            msg.setInformativeText(
                "Puedes encontrar Discord en:\n"
                "• Menú de aplicaciones\n"
                "• Terminal: discord\n\n"
                f"Instalado en: {Config.INSTALL_DIR}"
            )
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            
            logger.info("Instalación completada exitosamente")
            QTimer.singleShot(500, self.close)
        else:
            self._show_error("Error de instalación", message)
            self.install_button.setText("REINTENTAR")
            self.install_button.setEnabled(True)
    
    def _show_error(self, title, message):
        """Muestra un diálogo de error"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.exec()
        logger.error(f"{title}: {message}")
    
    def _show_help(self):
        """Muestra diálogo de ayuda"""
        help_text = f"""
        <h2>Discord Installer Pro v{Config.APP_VERSION}</h2>
        <p><b>Instalador profesional para Discord en Linux</b></p>
        
        <h3>Características:</h3>
        <ul>
            <li>Instalación automática desde archivo tar.gz</li>
            <li>Actualización de versiones existentes</li>
            <li>Creación de accesos directos</li>
            <li>Validación de archivos</li>
            <li>Sistema de logging completo</li>
        </ul>
        
        <h3>Requisitos:</h3>
        <ul>
            <li>Archivo discord-*.tar.gz en Descargas</li>
            <li>PolicyKit (pkexec) instalado</li>
            <li>500 MB de espacio libre</li>
        </ul>
        
        <h3>Ubicaciones:</h3>
        <ul>
            <li>Instalación: {Config.INSTALL_DIR}</li>
            <li>Logs: {Config.LOG_FILE}</li>
        </ul>
        
        <p><i>Desarrollado con ❤️ por Claude AI</i></p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Ayuda")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

def main():
    """Función principal de la aplicación"""
    try:
        logger.info(f"=== Iniciando {Config.APP_NAME} v{Config.APP_VERSION} ===")
        logger.info(f"Python: {sys.version}")
        logger.info(f"Sistema: {os.uname().sysname} {os.uname().release}")
        
        app = QApplication(sys.argv)
        app.setApplicationName(Config.APP_NAME)
        app.setApplicationVersion(Config.APP_VERSION)
        
        # Configurar fuente por defecto
        app.setFont(QFont("Segoe UI", 10))
        
        window = DiscordInstallerUI()
        window.show()
        
        exit_code = app.exec()
        logger.info(f"Aplicación finalizada con código: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.critical(f"Error fatal: {e}", exc_info=True)
        print(f"ERROR FATAL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
