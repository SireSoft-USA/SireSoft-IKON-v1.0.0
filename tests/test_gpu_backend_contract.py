import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from libs.core.gpu.backend import GPU_BACKEND
from cuda_status import probe


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    backend_file = ROOT / "libs" / "core" / "gpu" / "backend.py"
    cuda_file = ROOT / "libs" / "core" / "gpu" / "sireikon_cuda.cu"
    build_tool = ROOT / "tools" / "build_cuda_backend.py"
    gpu_test = ROOT / "tools" / "test_gpu_training.py"
    pipeline = ROOT / "tools" / "run_pipeline.py"
    root_pipeline = ROOT / "run_pipeline.py"
    cuda_status = ROOT / "tools" / "cuda_status.py"

    for path in (backend_file, cuda_file, build_tool, gpu_test, pipeline, root_pipeline, cuda_status):
        check(path.is_file(), "Required compute/pipeline file missing: " + str(path))

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

    pipeline_source = pipeline.read_text(encoding="utf-8")
    build_source = build_tool.read_text(encoding="utf-8")
    check('default="auto"' in pipeline_source, "pipeline must default to auto device mode")
    check("nvcc was not found" not in build_source, "obsolete nvcc hard-failure text is still present")
    check("prebuilt CUDA backend" in build_source, "build tool must support runtime use without nvcc")

    environment = probe()
    check("backend_exists" in environment, "CUDA environment probe missing backend state")
    check("nvcc" in environment, "CUDA environment probe missing compiler state")

    print("GPU BACKEND CONTRACT TEST: PASS")
    print("GPU required: no")
    print("CPU fallback: PASS")
    print("nvcc treated as build-time only: PASS")
    print("pipeline default device: auto")


if __name__ == "__main__":
    main()
