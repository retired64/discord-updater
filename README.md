<div align="center">
  <img src="icon.png" alt="Discord Updater Logo" width="120" height="120">
  
  # DiscordUpdate-TarGZ
  
  **Actualizador automático para la versión tar.gz de Discord en Linux.**
  <br>
  
  ![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
  ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
  ![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>


### ¿Por qué existe esto?

Si usas Linux (Fedora, Arch, Debian, etc.), conoces el dolor: sale una actualización de Discord, la aplicación se bloquea y te obliga a descargar un archivo `.tar.gz`. Los repositorios oficiales (`dnf`, `apt`, `pacman`) suelen tardar días en actualizarse, y la versión Flatpak ocupa mucho espacio.

Instalar el `tar.gz` manualmente cada vez (extraer, mover a `/opt`, actualizar enlaces) es tedioso. **Esta herramienta detecta el archivo descargado y actualiza tu instalación del sistema con un solo clic.**

---

### Requisitos

1. Tener **Discord** instalado (o querer instalarlo).
2. Descargar la actualización oficial (`discord-x.x.x.tar.gz`) desde la web de Discord.
3. **Importante:** Dejar el archivo en tu carpeta de **Descargas** (`~/Downloads` o `~/Descargas`).

---

### 🛠️ Cómo usarlo

1. **Descarga la actualización:** Cuando Discord te pida actualizar, baja el `.tar.gz` y déjalo en Descargas.
2. **Ejecuta el Actualizador:** Abre `DiscordUpdater` (doble clic o desde terminal).
3. **Verificación:**
   - 🟢 **Verde:** Archivo detectado correctamente.
   - 🔴 **Rojo:** No se encontró el `.tar.gz` en Descargas.
4. **Instalar:** Presiona **"INSTALAR / ACTUALIZAR"**.
5. **Autenticación:** El sistema te pedirá tu contraseña de usuario (usa `pkexec` para permisos seguros de root).

> **Nota:** La instalación toma solo unos segundos. Al finalizar, recibirás una notificación de éxito.

---

### ❓ FAQ

**¿Borrará mis datos o servidores?**
No. La herramienta solo reemplaza los binarios del sistema en `/usr/share/discord` (o `/opt`). Tu configuración de usuario (`~/.config/discord`) se mantiene intacta.

**La AppImage no abre al hacer doble clic**
Asegúrate de que el archivo tenga permisos de ejecución:
```bash
chmod +x DiscordUpdater-x86_64.AppImage
```

---

### ⚙️ Nota para usuarios de Gear Lever

Si utilizas **Gear Lever** para gestionar tus AppImages, es posible que recibas una advertencia indicando que el archivo es **"Inseguro"** o que **"Faltan metadatos"**.

Esto es normal, ya que esta aplicación es una herramienta local y no incluye una firma digital corporativa. Para integrarla correctamente:

1. Abre las **Preferencias** de Gear Lever.
2. Busca la sección de seguridad o validación.
3. Desactiva la opción de **"Verificar metadatos"** o activa **"Permitir AppImages sin firmar"**.
4. Arrastra el archivo de nuevo y se integrará sin problemas.
