<div align="center">

<img src="src/img/icon.png" alt="Discord Update Logo" width="120" height="120">

# Discord Update

**Actualizador automático de Discord (tar.gz) para Linux**

Una herramienta diseñada para integrar y mantener Discord actualizado en el sistema de forma limpia, segura y sin fricción.

</div>

---

![Discord Update](src/img/logo.png)

<div align="center">

![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge\&logo=linux\&logoColor=black)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

<p align="center">
  <img src="src/img/546908112-03e3e6b8-8a8e-4122-a301-1760972d8473.png" alt="Discord Update Linux">
</p>


---

## Contexto y motivación

En la mayoría de las distribuciones Linux (Fedora, Arch, Debian, entre otras), Discord presenta un comportamiento recurrente: cuando existe una nueva versión, la aplicación se bloquea y obliga al usuario a descargar manualmente un archivo `tar.gz` desde el sitio oficial.

Los repositorios del sistema (`dnf`, `apt`, `pacman`) suelen tardar en reflejar estas actualizaciones, y alternativas como Flatpak incrementan considerablemente el consumo de espacio y dependencias.

El proceso manual —extraer el archivo, moverlo a `/opt` o `/usr/share`, actualizar enlaces y permisos— resulta repetitivo y propenso a errores.

**Discord Update** nace para eliminar esa fricción: detecta automáticamente el archivo descargado y actualiza la instalación del sistema de manera controlada y transparente, en segundos.

---

## Características principales

* Detección automática del archivo `discord-*.tar.gz` descargado
* Instalación y actualización integrada al sistema
* Uso de permisos elevados de forma segura mediante `pkexec`
* Preservación total de la configuración y datos del usuario
* Compatible con múltiples distribuciones Linux
* Interfaz clara orientada a una sola acción: actualizar sin complicaciones

---

## Requisitos

Antes de utilizar la herramienta, asegúrate de cumplir con lo siguiente:

1. Tener Discord instalado o intención de instalarlo mediante el paquete oficial.
2. Descargar la actualización desde la página oficial de Discord en formato `tar.gz`.
3. Mantener el archivo descargado en la carpeta de **Descargas** del usuario:

   * `~/Downloads`
   * `~/Descargas`

La aplicación utiliza esta ubicación para realizar la detección automática.

---

## Uso

Discord Update está diseñado para funcionar sin configuración manual. El flujo es deliberadamente simple y automático, siguiendo el comportamiento real de Discord en Linux.

### Flujo de funcionamiento

1. **Descarga de la actualización oficial**
   Cuando Discord indique que existe una nueva versión, descarga el archivo oficial en formato `tar.gz` desde el sitio web de Discord.

2. **Ubicación del archivo**
   Coloca el archivo descargado en la carpeta de Descargas del usuario:

   * `~/Descargas`
   * `~/Downloads`

   La aplicación escanea automáticamente estas rutas y selecciona el archivo `discord-*.tar.gz` más reciente.

3. **Ejecución de Discord Update**
   Inicia la aplicación (AppImage o ejecutable). Al abrirse:

   * Se analiza el sistema
   * Se valida la existencia del archivo
   * Se actualiza la interfaz según el estado detectado

4. **Validación visual**

   * Estado positivo: se muestra el nombre del archivo detectado y el botón queda habilitado.
   * Estado negativo: se indica que no se encontró un archivo válido y no se permite continuar.

5. **Instalación / actualización**
   Al presionar **InstALAR / ACTUALIZAR**, la aplicación:

   * Genera dinámicamente un script de instalación temporal
   * Solicita permisos elevados mediante `pkexec`
   * Extrae el contenido del `tar.gz`
   * Reemplaza la instalación previa del sistema
   * Actualiza accesos directos, enlaces simbólicos y base de datos del escritorio

6. **Finalización**
   El proceso toma solo unos segundos. Al completarse:

   * Discord queda actualizado
   * La aplicación confirma el éxito
   * No es necesario reiniciar sesión ni el sistema

Este flujo evita pasos manuales, reduce errores y mantiene una integración limpia con el sistema.

---

## Seguridad y datos del usuario

La herramienta **no modifica ni elimina información personal**. Únicamente reemplaza los binarios de Discord ubicados en rutas del sistema como:

* `/usr/share/discord`
* `/opt/discord`

Los datos del usuario permanecen intactos en:

```text
~/.config/discord
```

Servidores, sesiones, configuraciones y caché no se ven afectados.

---

## Solución de problemas

### La AppImage no se ejecuta al hacer doble clic

Asegúrate de que el archivo tenga permisos de ejecución:

```bash
chmod +x DiscordUpdater-x86_64.AppImage
```

Luego vuelve a ejecutarlo.

---
### ⚠️ Aviso para usuarios de Window Managers (i3, Sway, BSPWM)
Este instalador utiliza `pkexec` para solicitar permisos de administrador de forma gráfica. Si utilizas un gestor de ventanas minimalista, **es obligatorio tener un agente de autenticación Polkit ejecutándose en segundo plano** (ej. `polkit-gnome`, `lxpolkit` o `mate-polkit`).

Si el instalador se queda "Cargando..." indefinidamente al intentar instalar, verifique que su agente de autenticación esté activo, ya que la ventana para introducir la contraseña no se está mostrando.

### 🚫 Incompatibilidad con Sistemas Inmutables
Este instalador requiere acceso de escritura a los directorios del sistema `/opt` y `/usr/local/bin`. Por lo tanto, **no es compatible** con distribuciones de sistema de archivos inmutable o de solo lectura, tales como:
* **SteamOS** (Steam Deck)
* **Fedora Silverblue / Kinoite**
* **openSUSE MicroOS**
* **NixOS**

Para estos sistemas, se recomienda utilizar la versión Flatpak de Discord o instalarlo dentro de un contenedor (Distrobox/Toolbox).

### 📋 Dependencias del Sistema
El script está diseñado para funcionar en la mayoría de distribuciones estándar (Ubuntu, Debian, Arch Linux, Fedora Workstation), pero requiere que las siguientes herramientas estén instaladas:
* `python3` con `PySide6` y `requests`.
* `pkexec` (PolicyKit) para la elevación de privilegios.
* `tar` para la descompresión de archivos.
* `update-desktop-database` (paquete `desktop-file-utils`) para actualizar los iconos del menú.

### 🛠️ Solución de Problemas
Si la instalación falla o se cierra inesperadamente, el instalador genera un registro detallado de errores. Puede consultar este archivo para obtener más información o adjuntarlo al reportar un problema:

**Ruta del log:** `~/.discord_installer.log`


## Nota para usuarios de Gear Lever

Si utilizas **Gear Lever** para gestionar AppImages, es posible que aparezca una advertencia indicando que el archivo es inseguro o que carece de metadatos.

Esto es un comportamiento esperado. Discord Update es una herramienta local y no incluye firma digital corporativa.

Para integrarla correctamente:

1. Abre las preferencias de Gear Lever.
2. Accede a la sección de seguridad o validación.
3. Desactiva la verificación estricta de metadatos o habilita la opción para permitir AppImages sin firmar.
4. Vuelve a arrastrar el archivo para completar la integración.

## ERROR
<img width="465" height="259" alt="Captura desde 2026-02-09 10-58-44" src="https://github.com/user-attachments/assets/23166410-2ba2-4be5-88cf-8db288fae978" />

## SOLUCION
- INgresa a preferencias de GearLever, Desactivar esta opcion (tal vez a futuro actualice correctamente los metadatos para actualizaciones automaticas dentro del mismo appimage y firmado, mientras esta es una solucion temporal)
<img width="627" height="146" alt="Captura desde 2026-02-09 10-55-15" src="https://github.com/user-attachments/assets/1005b6b9-6340-4167-b562-d16fe64fd050" />


---

## Licencia

Este proyecto se distribuye bajo la licencia **MIT**, permitiendo su uso, modificación y distribución libremente.

---

## Filosofía del proyecto

Discord Update no pretende reinventar el sistema de paquetes ni imponer dependencias innecesarias. Su objetivo es simple: respetar el flujo natural de Discord en Linux y automatizar la parte más incómoda del proceso, manteniendo el control en manos del usuario.

Si usas Linux a diario y prefieres soluciones limpias, directas y sin sobrecarga, esta herramienta fue creada para ti.
