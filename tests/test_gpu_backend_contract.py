import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from libs.core.gpu.backend import GPU_BACKEND


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    backend_file = ROOT / "libs" / "core" / "gpu" / "backend.py"
    cuda_file = ROOT / "libs" / "core" / "gpu" / "sireikon_cuda.cu"
    build_tool = ROOT / "tools" / "build_cuda_backend.py"
    gpu_test = ROOT / "tools" / "test_gpu_training.py"

    check(backend_file.is_file(), "CUDA Python backend missing")
    check(cuda_file.is_file(), "CUDA kernel source missing")
    check(build_tool.is_file(), "CUDA build tool missing")
    check(gpu_test.is_file(), "GPU training test missing")

    status = GPU_BACKEND.configure("cpu", 0, strict=True)
    check(status["active"] == "cpu", "CPU fallback must work without a GPU")
    check(GPU_BACKEND.enabled() is False, "GPU backend should be disabled in forced CPU mode")

    source = cuda_file.read_text(encoding="utf-8")
    required_symbols = (
        "sireikon_cuda_matmul",
        "sireikon_cuda_attention_forward",
        "sireikon_cuda_attention_backward",
        "sireikon_cuda_layernorm_forward",
        "sireikon_cuda_layernorm_backward",
        "sireikon_cuda_cross_entropy_forward",
        "sireikon_cuda_cross_entropy_backward",
        "sireikon_cuda_adamw",
    )
    for symbol in required_symbols:
        check(symbol in source, "Missing CUDA symbol: " + symbol)

    print("GPU BACKEND CONTRACT TEST: PASS")
    print("GPU required: no")
    print("CPU fallback: PASS")


if __name__ == "__main__":
    main()
