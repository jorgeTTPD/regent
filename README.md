# 🎙️ Regent — Asistente por voz (v1)

Asistente personal por voz **one-shot** para Linux: hablas una orden, se transcribe con Whisper y la ejecuta [Antigravity CLI](https://github.com/google/antigravity-cli) (`agy`).

> **v1 — PoC funcional.** Sin empaquetar, sin daemon, sin interfaz gráfica: solo el puente.

> **🧩 Versión genérica**
>
> Este repositorio contiene una **versión genérica y limpia** del proyecto, publicada para que **cualquiera** pueda usarla, modificarla y adaptarla a su sistema.
>
> La **versión personal** del autor está completamente **integrada y personalizada** para su propia máquina Arch Linux (atajos, scripts y configuración del sistema) y **no está publicada** — solo el autor tiene acceso a ella.
>
> Filosofía Arch: toma la base, constrúyela y hazla tuya. 🐧

## ✨ Cómo funciona

```
super+o  →  graba audio en RAM  →  whisper transcribe  →  agy -p ejecuta  →  muere
```

- **One-shot**: no hay proceso en segundo plano ni consumo en reposo.
- **Grabación en RAM**: nunca toca el disco (ni archivos temporales).
- **Detección de silencio**: se detiene solo cuando dejas de hablar (máx. 8 s).
- **Ejemplos de órdenes**:
  - *"Abre YouTube y pon Artpop de Lady Gaga"*
  - *"Crea una carpeta llamada fotos en el escritorio"*

## 📦 Requisitos

- Python 3.10+
- [Antigravity CLI](https://github.com/google/antigravity-cli) (`agy`) en el PATH
- `notify-send` (libnotify)
- Un micrófono funcional (PipeWire/PulseAudio)

## 🚀 Instalación

```bash
# 1. Clona y crea el entorno
git clone https://github.com/jorgeTTPD/regent.git
cd regent
python3 -m venv .venv

# 2. Dependencias
.venv/bin/pip install faster-whisper sounddevice numpy

# 3. Permisos de agy (headless): permite ejecutar comandos y archivos sin prompt
#    en ~/.gemini/antigravity-cli/settings.json
"permissions": {
  "allow": [
    "command(*)", "write_file(*)", "edit(*)", "read_file(*)", "bash(*)"
  ]
}
```

## 🎤 Uso

```bash
# Directo desde terminal
./puente.py

# Modo test: comprueba el nivel de tu micrófono
./puente.py --test --segundos 5
```

### Atajo de teclado (sxhkd)

```bash
# ~/.config/sxhkd/sxhkdrc
super + o
    /ruta/al/puente.py
```

## ⚙️ Configuración (variables de entorno)

| Variable | Descripción | Default |
|---|---|---|
| `VA_MODEL` | Modelo de Whisper | `base` |
| `VA_LANG` | Idioma | `es` |
| `VA_MAX_SECONDS` | Duración máx. de grabación (s) | `8` |
| `VA_SILENCE_DB` | Umbral de silencio (dB) | `-35` |
| `VA_DEVICE` | Dispositivo de audio | auto |
| `VA_TIMEOUT` | Timeout de agy (s) | `120` |
| `VA_INITIAL_SILENCE` | Máx. sin hablar antes de abortar (s) | `3` |

## 🛡️ Seguridad

- El sistema no guarda API keys: usa el login de Antigravity CLI.
- Prompt de sistema con reglas: no tocar `~/.ssh`, `~/.gnupg`, credenciales; mover a la papelera antes de borrar; no ejecutar `curl|bash`.
- ⚠️ **Advertencia**: con `command(*)` y `bash(*)`, `agy` ejecuta órdenes sin confirmación. Úsalo solo en tu propia máquina y a tu riesgo.

## 📌 Roadmap

- [ ] Interfaz gráfica (eww) para ver la transcripción en pantalla
- [ ] Empaquetado e instalador
- [ ] Lista `deny` de comandos peligrosos

## 📄 Licencia

MIT
