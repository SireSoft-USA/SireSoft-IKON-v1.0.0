import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from libs.core.gpu.backend import GPU_BACKEND
from cuda_status import CUDA_METADATA, probe


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    backend_file = ROOT / "libs" / "core" / "gpu" / "backend.py"
    cuda_file = ROOT / "libs" / "core" / "gpu" / "sireikon_cuda.cu"
    build_tool = ROOT / "tools" / "build_cuda_backend.py"
    metadata_tool = ROOT / "tools" / "write_cuda_build_metadata.py"
    gpu_test = ROOT / "tools" / "test_gpu_training.py"
    pipeline = ROOT / "tools" / "run_pipeline.py"
    root_pipeline = ROOT / "run_pipeline.py"
    cuda_status = ROOT / "tools" / "cuda_status.py"
    workflow = ROOT / ".github" / "workflows" / "build-cuda-backend.yml"

    for path in (
        backend_file,
        cuda_file,
        build_tool,
        metadata_tool,
        gpu_test,
        pipeline,
        root_pipeline,
        cuda_status,
        workflow,
    ):
        check(path.is_file(), "Required compute/pipeline file missing: " + str(path))

    status = GPU_BACKEND.configure("cpu", 0, strict=True)
    check(status["active"] == "cpu", "CPU mode must work without a GPU")
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
    workflow_source = workflow.read_text(encoding="utf-8")

    check('default="cuda"' in pipeline_source, "production pipeline must default to strict CUDA")
    check("nvcc_info" not in pipeline_source, "runtime pipeline must not inspect/use nvcc")
    check("build_cuda_backend.py" in pipeline_source, "pipeline error guidance must point to build workflow/tool")
    check("subprocess.run(command" in build_source, "developer build tool must invoke nvcc")
    check("--cudart=static" in build_source, "prebuilt backend should statically link cudart")
    check("sm_61" in build_source, "build tool must support the P5000 sm_61 target")
    check("nvidia/cuda:12." in workflow_source, "GitHub workflow must build with CUDA 12.x")
    check("contents: write" in workflow_source, "workflow must be able to commit the built backend")
    check("libsireikon_cuda.so" in workflow_source, "workflow must produce the runtime shared library")
    check("libsireikon_cuda.build.json" in workflow_source, "workflow must commit build metadata")

    environment = probe()
    check("backend_exists" in environment, "CUDA environment probe missing backend state")
    check("backend_current" in environment, "CUDA environment probe missing source/binary freshness state")
    check("nvcc" in environment, "CUDA environment probe missing build-only compiler state")

    # The portable source ZIP intentionally may not contain a compiled .so yet;
    # GitHub Actions creates it after the source is pushed. Metadata is required
    # whenever the binary exists.
    if environment["backend_exists"]:
        check(CUDA_METADATA.is_file(), "checked-in CUDA backend must include build metadata")

    print("GPU BACKEND CONTRACT TEST: PASS")
    print("runtime nvcc dependency: none")
    print("production default: strict CUDA")
    print("build target: linux-x86_64 sm_61")
    print("build path: GitHub Actions or Linux CUDA 12.x development machine")


if __name__ == "__main__":
    main()
