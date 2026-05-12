from dataclasses import dataclass


@dataclass
class GpuStats:
    name: str
    load_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: float | None


def get_gpu_stats() -> list[GpuStats]:
    results = _try_nvidia()
    if results:
        return results
    return _try_amd()


def _try_nvidia() -> list[GpuStats]:
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        out = []
        for g in gpus:
            out.append(GpuStats(
                name=g.name,
                load_percent=round(g.load * 100, 1),
                memory_used_mb=round(g.memoryUsed, 1),
                memory_total_mb=round(g.memoryTotal, 1),
                temperature_c=g.temperature,
            ))
        return out
    except Exception:
        return []


def _try_amd() -> list[GpuStats]:
    try:
        import pyamdgpuinfo
        gpu = pyamdgpuinfo.get_gpu(0)
        load = gpu.query_load()
        mem_used = gpu.query_vram_usage()
        mem_total = gpu.memory_info["vram_size"]
        temp = gpu.query_temperature()
        return [GpuStats(
            name=gpu.name,
            load_percent=round(load * 100, 1),
            memory_used_mb=round(mem_used / 1024 / 1024, 1),
            memory_total_mb=round(mem_total / 1024 / 1024, 1),
            temperature_c=round(temp, 1) if temp else None,
        )]
    except Exception:
        return []
