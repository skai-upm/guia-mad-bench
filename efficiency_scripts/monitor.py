from __future__ import annotations

import psutil
import pynvml
import time
import csv
import subprocess
import statistics
import sys
import types
import platform
import json
import os
from codecarbon import EmissionsTracker

use_pynvml = False
use_smi = True  # Forzamos smi ya que pynvml es inaccesible
has_gpu = True  # Asumimos que tenemos acceso a nvidia-smi

# Verificamos si realmente tenemos acceso a nvidia-smi
try:
    subprocess.check_output(["nvidia-smi"], stderr=subprocess.STDOUT)
    print("[GUIA-MADBENCH-RESOURCE-MONITOR] nvidia-smi detected.")
except Exception:
    has_gpu = False
    print("[GUIA-MADBENCH-RESOURCE-MONITOR] nvidia-smi not available.")


# ---------------------------------------------------------------------------
# CodeCarbon puede fallar con "Insufficient Permissions" al intentar leer la
# potencia de la GPU vía NVML (nvmlDeviceGetPowerUsage / GetTotalEnergy...).
# Esto ocurre en muchos drivers de datacenter que restringen esa telemetría
# a usuarios con privilegios elevados, aunque "nvidia-smi" básico sí funcione
# (solo lee info estática). Como no podemos tocar permisos del servidor,
# si CodeCarbon falla al arrancar reintentamos "engañándolo" con un módulo
# pynvml falso, para que detecte que no hay GPU disponible y siga midiendo
# solo CPU/RAM sin lanzar excepción. Esto NO afecta al pynvml real que usa
# el resto del script (import pynvml, arriba), solo al que ve CodeCarbon.
# ---------------------------------------------------------------------------
def _build_disabled_pynvml_module():
    """
    En vez de simular un error de NVML (cuyo tipo exacto no podemos
    garantizar que CodeCarbon capture en cada punto interno de su código),
    simulamos el camino MUCHO más común y mejor probado: "esta máquina no
    tiene ninguna GPU NVIDIA". nvmlInit() se completa sin problemas y
    nvmlDeviceGetCount() devuelve 0, así que cualquier bucle interno de
    CodeCarbon sobre los dispositivos simplemente no itera ninguna vez y
    no hay ninguna excepción que capturar.
    """
    fake = types.ModuleType("pynvml")

    fake.nvmlInit = lambda: None
    fake.nvmlShutdown = lambda: None
    fake.nvmlDeviceGetCount = lambda: 0

    def _no_device(*args, **kwargs):
        raise IndexError("No GPU available")

    fake.nvmlDeviceGetHandleByIndex = _no_device

    # Reutilizamos la clase NVMLError real si pynvml estaba disponible, por si
    # algún módulo de codecarbon la referencia en un "except pynvml.NVMLError".
    fake.NVMLError = getattr(pynvml, "NVMLError", Exception)

    return fake


def _disable_codecarbon_gpu_tracking():
    """
    CodeCarbon importa `pynvml` dentro de sus propios submódulos (p. ej.
    codecarbon.core.gpu) en el momento en que el paquete se carga. Por eso
    NO basta con reemplazar sys.modules["pynvml"] después: esos submódulos
    ya tienen su propia referencia interna al pynvml real y la seguirán
    usando.

    Aquí recorremos todos los módulos ya cargados cuyo nombre empiece por
    "codecarbon" y, si tienen un atributo `pynvml`, lo sustituimos por un
    módulo falso cuyas funciones lanzan una excepción controlada
    (pynvml.NVMLError). CodeCarbon ya sabe capturar ese tipo de excepción
    internamente (es la misma clase que él usa para GPUs no disponibles),
    así que interpretará que no hay GPU y seguirá solo con CPU/RAM.
    """
    fake_pynvml = _build_disabled_pynvml_module()
    patched_modules = []

    for name, mod in list(sys.modules.items()):
        if mod is None or not name.startswith("codecarbon"):
            continue
        if hasattr(mod, "pynvml"):
            setattr(mod, "pynvml", fake_pynvml)
            patched_modules.append(name)

    # Por si algún submódulo hace "import pynvml" más tarde de forma perezosa
    sys.modules["pynvml"] = fake_pynvml

    if patched_modules:
        print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] GPU/NVML disabled in: {', '.join(patched_modules)}")
    else:
        print("[GUIA-MADBENCH-RESOURCE-MONITOR] WARNING: no 'pynvml' CodeCarbon module available.")

    return patched_modules


def start_emissions_tracker():
    """
    Intenta iniciar CodeCarbon con seguimiento completo (CPU+RAM+GPU).
    Si falla (p. ej. por falta de permisos NVML para leer potencia de GPU),
    reintenta automáticamente con la GPU deshabilitada, sin necesidad de
    tocar el servidor. Si aun así falla, continúa sin CodeCarbon en vez de
    abortar todo el benchmark.
    """
    try:
        tracker = EmissionsTracker()
        tracker.start()
        print("[GUIA-MADBENCH-RESOURCE-MONITOR] CodeCarbon successfully initialized.")
        return tracker
    except Exception as e:
        print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] WARNING: CodeCarbon failed to start with GPU: {e}")
        print("[GUIA-MADBENCH-RESOURCE-MONITOR] Restarting in CPU+RAM only mode...")

        _disable_codecarbon_gpu_tracking()

        try:
            tracker = EmissionsTracker()
            tracker.start()
            print("[GUIA-MADBENCH-RESOURCE-MONITOR] CodeCarbon successfully initiated in CPU+RAM only mode.")
            return tracker
        except Exception as e2:
            print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] ERROR: CodeCarbon failed to start: {e2}")
            cc_modules = sorted(m for m in sys.modules if m.startswith("codecarbon"))
            print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] DEBUG: Codecarbon loaded: {cc_modules}")
            print("[GUIA-MADBENCH-RESOURCE-MONITOR] Continuing execution without emissions data.")
            return None


def extract_hardware_specs(emissions, output_file='results/hardware_specs.json'):
    specs = {}

    # 1. Operating System Information
    specs["System"] = {
        "OS": platform.system(),
        "Release": platform.release(),
        "Architecture": platform.machine(),
        "Node_Name": platform.node()
    }

    # 2. CPU Information
    specs["CPU"] = {
        "Model": platform.processor(),
        "Physical_Cores": psutil.cpu_count(logical=False),
        "Logical_Cores_Threads": psutil.cpu_count(logical=True),
        "Max_Frequency_GHz": round(psutil.cpu_freq().max / 1000, 2) if psutil.cpu_freq() else "Unknown"
    }

    # 3. RAM Information
    ram = psutil.virtual_memory()
    specs["RAM"] = {
        "Total_GB": round(ram.total / (1024 ** 3), 2)
    }

    # 4. GPU Information (NVIDIA)
    specs["GPU"] = []
    if has_gpu:
        if use_pynvml:
            try:
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)

                    gpu_name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(gpu_name, bytes):
                        gpu_name = gpu_name.decode('utf-8')

                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

                    specs["GPU"].append({
                        "ID": i,
                        "Model": gpu_name,
                        "Total_VRAM_GB": round(mem.total / (1024 ** 3), 2)
                    })
                pynvml.nvmlShutdown()
            except Exception as e:
                specs["GPU"].append({"Error": f"Could not read GPU info via pynvml: {str(e)}"})

        elif use_smi:
            try:
                # nvidia-smi devuelve la memoria en MiB cuando se usa --query-gpu
                cmd = ["nvidia-smi", "--query-gpu=index,name,memory.total", "--format=csv,noheader,nounits"]
                result = subprocess.check_output(cmd, text=True)

                for line in result.strip().split('\n'):
                    parts = line.split(', ')
                    if len(parts) >= 3:
                        specs["GPU"].append({
                            "ID": int(parts[0]),
                            "Model": parts[1],
                            # Convertimos de MiB a GB dividiendo por 1024
                            "Total_VRAM_GB": round(float(parts[2]) / 1024, 2)
                        })
            except Exception as e:
                specs["GPU"].append({"Error": f"Could not read GPU info via nvidia-smi: {str(e)}"})
    else:
        specs["GPU"].append({"Warning": "No NVIDIA GPU found or accessible."})

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(specs, f, indent=4, ensure_ascii=False)

    print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] Hardware specifications successfully saved to: {output_file}")

    print("\n--- Hardware Summary ---")
    print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] OS:  {specs['System']['OS']} {specs['System']['Release']}")
    print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] CPU: {specs['CPU']['Model']} ({specs['CPU']['Logical_Cores_Threads']} Threads)")
    print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] RAM: {specs['RAM']['Total_GB']} GB")
    print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] Emissions: {emissions} kg CO2")
    for idx, gpu in enumerate(specs['GPU']):
        if "Model" in gpu:
            print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] GPU {idx}: {gpu['Model']} ({gpu['Total_VRAM_GB']} GB VRAM)")


def _write_summary(total_time, hist_cpu, hist_ram, hist_gpu_util, hist_gpu_vram, emissions):
    print("[GUIA-MADBENCH-RESOURCE-MONITOR] Summarizing consumptions")
    if not hist_cpu:
        hist_cpu, hist_ram, hist_gpu_util, hist_gpu_vram = [0], [0], [0], [0]

    summary = {
        "Total_Seconds": f"{total_time:.2f}",
        "CPU_Media_Percent": f"{statistics.mean(hist_cpu):.2f}",
        "CPU_Pico_Percent": f"{max(hist_cpu):.2f}",
        "RAM_Media_MB": f"{statistics.mean(hist_ram):.2f}",
        "RAM_Pico_MB": f"{max(hist_ram):.2f}",
        "GPU_Util_Media_Percent": f"{statistics.mean(hist_gpu_util):.2f}",
        "GPU_Util_Pico_Percent": f"{max(hist_gpu_util):.2f}",
        "GPU_VRAM_Media_MB": f"{statistics.mean(hist_gpu_vram):.2f}",
        "GPU_VRAM_Pico_MB": f"{max(hist_gpu_vram):.2f}",
        "Emissions": f"{emissions:.2f}"
    }

    with open('results/monitor_results_summary.csv', mode='w+', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(summary.keys())
        writer.writerow(summary.values())

    print("[GUIA-MADBENCH-RESOURCE-MONITOR] Execution summary successfully exported!")


def monitor_process(process):
    print("[GUIA-MADBENCH-RESOURCE-MONITOR] Initializing monitor")
    print("[GUIA-MADBENCH-RESOURCE-MONITOR] Monitoring process %s" % process)

    historial_cpu = []
    historial_ram = []
    historial_gpu_util = []
    historial_gpu_vram = []
    start_time = time.time()

    if use_pynvml:
        try:
            pynvml.nvmlInit()
        except:
            pass

    with open('results/monitor_results.csv', mode='w+', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Time_s", "CPU_Percent", "RAM_MB", "GPU_Util_Percent", "GPU_VRAM_MB"])

        m_process = subprocess.Popen(process)

        try:
            ps_process = psutil.Process(m_process.pid)

            while m_process.poll() is None:
                actual_time = time.time() - start_time

                try:
                    cpu = ps_process.cpu_percent(interval=None)
                    ram = ps_process.memory_info().rss / (1024 * 1024)
                except psutil.NoSuchProcess:
                    break

                gpu_util, gpu_mem = 0, 0
                if has_gpu:
                    if use_pynvml:
                        try:
                            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                            gpu_util = util.gpu
                            gpu_mem = mem.used / (1024 * 1024)
                        except Exception:
                            pass
                    elif use_smi:
                        try:
                            cmd = ["nvidia-smi", "-i", "0", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"]
                            res = subprocess.check_output(cmd, text=True).strip()
                            parts = res.split(', ')
                            if len(parts) == 2:
                                gpu_util = float(parts[0])
                                gpu_mem = float(parts[1])
                        except Exception:
                            pass

                writer.writerow([f"{actual_time:.2f}", cpu, ram, gpu_util, gpu_mem])

                historial_cpu.append(cpu)
                historial_ram.append(ram)
                historial_gpu_util.append(gpu_util)
                historial_gpu_vram.append(gpu_mem)

                time.sleep(0.5)

        except Exception as e:
            print("[GUIA-MADBENCH-RESOURCE-MONITOR] ERROR! Something happened while monitoring process: %s" % e)

        finally:
            m_process.wait()
            total_time = time.time() - start_time

            if use_pynvml:
                try:
                    pynvml.nvmlShutdown()
                except:
                    pass

    print("[GUIA-MADBENCH-RESOURCE-MONITOR] Finished execution detected")
    print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] Total execution time: {total_time:.2f} seconds")
    print("[GUIA-MADBENCH-RESOURCE-MONITOR] Monitoring results successfully saved")

    # Devolvemos los datos para poder generar el resumen al final
    return total_time, historial_cpu, historial_ram, historial_gpu_util, historial_gpu_vram


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("[GUIA-MADBENCH-RESOURCE-MONITOR] Usage: python monitor.py <command to execute>")
        sys.exit(1)

    # Asegurar que el directorio de resultados existe
    os.makedirs('results', exist_ok=True)

    tracker = start_emissions_tracker()

    # Recogemos los historiales para escribir el resumen después
    total_time, hist_cpu, hist_ram, hist_gpu_util, hist_gpu_vram = monitor_process(args)

    # Detenemos el tracker PRIMERO para poder obtener las emisiones reales
    emissions = 0.0
    if tracker is not None:
        try:
            emissions = tracker.stop() or 0.0
        except Exception as e:
            print(f"[GUIA-MADBENCH-RESOURCE-MONITOR] WARNING: CodeCarbon failed to stop: {e}")
            emissions = 0.0
    else:
        print("[GUIA-MADBENCH-RESOURCE-MONITOR] WARNING: No emissions data available.")

    # Ahora sí podemos escribir el resumen de los CSV y las características hardware
    _write_summary(total_time, hist_cpu, hist_ram, hist_gpu_util, hist_gpu_vram, emissions)
    extract_hardware_specs(emissions)
