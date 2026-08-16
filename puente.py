

import argparse
import os
import subprocess
import sys

import numpy as np


MODEL = os.environ.get("VA_MODEL", "base")
LANG = os.environ.get("VA_LANG", "es")
MAX_SECONDS = float(os.environ.get("VA_MAX_SECONDS", "8"))
SILENCE_DB = float(os.environ.get("VA_SILENCE_DB", "-35"))
DEVICE = os.environ.get("VA_DEVICE", None)
AGY_TIMEOUT = int(os.environ.get("VA_TIMEOUT", "120"))
INITIAL_SILENCE = float(os.environ.get("VA_INITIAL_SILENCE", "3"))
SAMPLE_RATE = 16000  
CHUNK_SECONDS = 0.3  
SILENCE_CHUNKS = 2   

SYSTEM_PROMPT = """Eres un asistente personal por voz con acceso a los archivos del usuario (~).
Reglas obligatorias:
1. Nunca toques ~/.ssh, ~/.gnupg, ~/.password-store ni archivos de credenciales/tokens.
2. Para borrar o sobrescribir algo, primero muévelo a la papelera o pregunta antes.
3. No ejecutes comandos que descarguen y ejecuten código en un solo paso (curl|bash, wget|bash).
4. Opera siempre dentro de ~ a menos que la orden lo justifique.
5. Responde en español, de forma breve.
Ejecuta la orden del usuario usando herramientas de terminal y confirma lo que hiciste."""



def _abrir_stream(sd, dispositivo):
    
    try:
        return sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", device=dispositivo
        )
    except Exception as exc:
        if dispositivo is not None:
            print(
                f"⚠️  No se pudo usar '{dispositivo}' a {SAMPLE_RATE} Hz: {exc}",
                file=sys.stderr,
            )
            print("   Probando con el dispositivo por defecto...", file=sys.stderr)
            return sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32", device=None
            )
        raise


def grabar() -> np.ndarray:
    try:
        import sounddevice as sd
    except ImportError:
        print("❌ Falta sounddevice. Instala: .venv/bin/pip install sounddevice", file=sys.stderr)
        _notificar("Asistente", "❌ Falta sounddevice (.venv/bin/pip install)")
        sys.exit(1)

    print("🎤 Escuchando...", file=sys.stderr)

    audio = []
    hablando = False
    silencios = 0
    total_muestras = 0
    chunk_len = int(SAMPLE_RATE * CHUNK_SECONDS)
    max_muestras = int(SAMPLE_RATE * MAX_SECONDS)
    max_silencio_inicial = int(SAMPLE_RATE * INITIAL_SILENCE)

    try:
        with _abrir_stream(sd, DEVICE) as stream:
            while True:
                data, _ = stream.read(chunk_len)
                rms = float(np.sqrt(np.mean(data**2)))
                db = 20.0 * np.log10(rms + 1e-12)

                if db > SILENCE_DB:
                    hablando = True
                    silencios = 0
                elif hablando:
                    silencios += 1

                audio.append(data.copy())
                total_muestras += chunk_len

                
                if not hablando and total_muestras >= max_silencio_inicial:
                    return np.array([])

                if (hablando and silencios >= SILENCE_CHUNKS) or total_muestras >= max_muestras:
                    break
    except Exception as exc:  # dallo al grabar
        print(f"❌ Error con el micrófono: {exc}", file=sys.stderr)
        _notificar("Asistente", "❌ Error con el micrófono")
        sys.exit(1)

    return np.concatenate(audio, axis=0).reshape(-1) if audio else np.array([])



def test_mic(segundos: float = 4.0) -> None:
    if segundos <= 0:
        segundos = 4.0
    try:
        import sounddevice as sd
    except ImportError:
        print("❌ Falta sounddevice. Instala: pip install sounddevice", file=sys.stderr)
        sys.exit(1)

    print(f"🎤 Grabando {segundos:.0f}s... ¡HABLA AHORA!", file=sys.stderr)
    niveles = []
    chunk = int(SAMPLE_RATE * 0.1)
    max_muestras = int(SAMPLE_RATE * segundos)

    try:
        with _abrir_stream(sd, DEVICE) as stream:
            try:
                nombre_dev = sd.query_devices(stream.device)["name"]
                print(f"🎙️  Dispositivo: {nombre_dev}", file=sys.stderr)
            except Exception as exc:
                print(f"⚠️  No se pudo leer el nombre del dispositivo: {exc}", file=sys.stderr)
            muestras = 0
            while muestras < max_muestras:
                data, _ = stream.read(chunk)
                rms = float(np.sqrt(np.mean(data**2)))
                db = 20.0 * np.log10(rms + 1e-12)
                niveles.append(db)
                muestras += chunk
                barra = "#" * max(0, min(20, int((db + 100) / 5)))
                print(f"  {db:7.1f} dB {barra}", file=sys.stderr)
    except Exception as exc:
        print(f"❌ Error con el micrófono: {exc}", file=sys.stderr)
        sys.exit(1)

    mejor = max(niveles) if niveles else -240.0
    print(f"\n📊 Nivel máximo: {mejor:.1f} dB", file=sys.stderr)
    if mejor > SILENCE_DB:
        print("✅ El micrófono detecta tu voz.", file=sys.stderr)
    else:
        print(
            "⚠️  No se detectó señal. ¿Micrófono muteado, en silencio, o dispositivo equivocado?",
            file=sys.stderr,
        )



def transcribir(audio: np.ndarray) -> str:
    from faster_whisper import WhisperModel

    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, language=LANG, beam_size=1, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments).strip()



def ejecutar(texto: str) -> None:
    prompt = f"{SYSTEM_PROMPT}\n\nOrden del usuario: {texto}"
    print(f"🤖 Enviando a agy...", file=sys.stderr)

    try:
        proc = subprocess.run(
            ["agy", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=AGY_TIMEOUT,
        )
    except FileNotFoundError:
        print("❌ 'agy' no está instalado o no está en el PATH.", file=sys.stderr)
        _notificar("Asistente", "❌ 'agy' no está instalado o no está en el PATH")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        msg = f"⏱️ agy tardó más de {AGY_TIMEOUT}s, abortando."
        print(msg, file=sys.stderr)
        _notificar("Asistente", msg)
        sys.exit(1)

    salida = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    print(salida)

    if proc.returncode != 0:
        _notificar("Asistente", f"❌ agy falló (código {proc.returncode})")
    else:
        _notificar("Resultado", salida[:400] or "✅ Listo")


def _notificar(titulo: str, mensaje: str) -> None:
    subprocess.run(
        ["notify-send", "-a", "Asistente", titulo, mensaje],
        check=False,
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Puente de voz → Antigravity CLI (one-shot)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Modo prueba: graba unos segundos y muestra el nivel de señal sin enviar a agy",
    )
    parser.add_argument(
        "--segundos",
        type=float,
        default=4.0,
        help="Duración de la grabación en modo test (default: 4)",
    )
    args = parser.parse_args()

    if args.test:
        test_mic(args.segundos)
        return

    audio = grabar()
    if len(audio) < SAMPLE_RATE * 0.3:
        _notificar("Asistente", "No escuché nada. Inténtalo de nuevo.")
        sys.exit(0)

    print("✍️ Transcribiendo...", file=sys.stderr)
    try:
        texto = transcribir(audio)
    except ImportError:
        print(
            "❌ Falta faster-whisper. Instala: .venv/bin/pip install faster-whisper",
            file=sys.stderr,
        )
        _notificar("Asistente", "❌ Falta faster-whisper (.venv/bin/pip install)")
        sys.exit(1)

    if not texto:
        _notificar("Asistente", "No pude entender la orden.")
        sys.exit(0)

    print(f"🗣️  Dijiste: {texto}")
    _notificar("Transcripción", texto)

    ejecutar(texto)


if __name__ == "__main__":
    main()
