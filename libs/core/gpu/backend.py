"""Optional custom CUDA compute backend for SireSoft-IKON-v1.0.

This module uses only Python's standard library (ctypes/os/pathlib).  The
numerical kernels live in ``sireikon_cuda.cu`` and are compiled with NVIDIA's
CUDA compiler into ``libsireikon_cuda.so``.  No PyTorch, TensorFlow, NumPy,
CuPy, Numba, cuBLAS, or other Python numerical/ML package is used.

The rest of the project remains functional without CUDA: ``auto`` mode falls
back to the existing handwritten CPU implementation and ``cpu`` mode forces
that path.  ``cuda`` mode is strict and fails early if the native backend is
not available.
"""

import ctypes
import os
from pathlib import Path


class CudaBackend:
    _MODE_CODES = {
        "add": 0,
        "subtract": 1,
        "multiply": 2,
        "divide": 3,
    }

    _UNARY_CODES = {
        "exp": 0,
        "log": 1,
        "tanh": 2,
        "sigmoid": 3,
        "relu": 4,
    }

    def __init__(self):
        self.requested = str(os.getenv("SIREIKON_DEVICE", "auto")).lower()
        self.device_index = int(os.getenv("SIREIKON_CUDA_DEVICE", "0"))
        self.active = "cpu"
        self.library_path = None
        self.library = None
        self.load_error = None
        self.calls = {}
        self._try_load()
        self.configure(self.requested, self.device_index, strict=False)

    def _candidate_paths(self):
        explicit = os.getenv("SIREIKON_CUDA_LIBRARY")
        paths = []
        if explicit:
            paths.append(Path(explicit))
        paths.extend([
            Path("libs/core/gpu/libsireikon_cuda.so"),
            Path("libs/core/gpu/sireikon_cuda.dll"),
            Path("libs/core/gpu/libsireikon_cuda.dylib"),
        ])
        return paths

    def _try_load(self):
        for path in self._candidate_paths():
            try:
                if not path.is_file():
                    continue
                library = ctypes.CDLL(str(path.resolve()))
                self.library = library
                self.library_path = str(path.resolve())
                self._bind_signatures()
                return
            except Exception as error:
                self.library = None
                self.library_path = None
                self.load_error = str(error)
        if self.load_error is None:
            self.load_error = (
                "precompiled CUDA runtime library is missing: "
                "libs/core/gpu/libsireikon_cuda.so. "
                "Build it in GitHub Actions (Build CUDA Backend) or on a Linux "
                "development machine with CUDA 12.x, then deploy the compiled library."
            )

    def _bind_signatures(self):
        lib = self.library
        c_int = ctypes.c_int
        c_float = ctypes.c_float
        p_float = ctypes.POINTER(c_float)
        p_int = ctypes.POINTER(c_int)

        lib.sireikon_cuda_device_count.argtypes = [p_int]
        lib.sireikon_cuda_device_count.restype = c_int
        lib.sireikon_cuda_set_device.argtypes = [c_int]
        lib.sireikon_cuda_set_device.restype = c_int
        lib.sireikon_cuda_synchronize.argtypes = []
        lib.sireikon_cuda_synchronize.restype = c_int
        lib.sireikon_cuda_last_error.argtypes = []
        lib.sireikon_cuda_last_error.restype = ctypes.c_char_p

        lib.sireikon_cuda_binary_broadcast.argtypes = [
            p_float, p_int, c_int,
            p_float, p_int, c_int,
            p_int, c_int, c_int, p_float,
        ]
        lib.sireikon_cuda_binary_broadcast.restype = c_int

        lib.sireikon_cuda_unary.argtypes = [p_float, c_int, c_int, p_float]
        lib.sireikon_cuda_unary.restype = c_int
        lib.sireikon_cuda_power.argtypes = [p_float, c_int, c_float, p_float]
        lib.sireikon_cuda_power.restype = c_int
        lib.sireikon_cuda_activation_backward.argtypes = [
            p_float, p_float, p_float, c_int, c_int, c_float, p_float
        ]
        lib.sireikon_cuda_activation_backward.restype = c_int
        lib.sireikon_cuda_sum.argtypes = [p_float, c_int, p_float]
        lib.sireikon_cuda_sum.restype = c_int
        lib.sireikon_cuda_sum_squares.argtypes = [p_float, c_int, p_float]
        lib.sireikon_cuda_sum_squares.restype = c_int
        lib.sireikon_cuda_scale.argtypes = [p_float, c_int, c_float, p_float]
        lib.sireikon_cuda_scale.restype = c_int
        lib.sireikon_cuda_transpose2d.argtypes = [p_float, c_int, c_int, p_float]
        lib.sireikon_cuda_transpose2d.restype = c_int
        lib.sireikon_cuda_matmul.argtypes = [p_float, p_float, c_int, c_int, c_int, p_float]
        lib.sireikon_cuda_matmul.restype = c_int
        lib.sireikon_cuda_extract_head.argtypes = [
            p_float, c_int, c_int, c_int, c_int, c_int, p_float
        ]
        lib.sireikon_cuda_extract_head.restype = c_int
        lib.sireikon_cuda_scatter_head.argtypes = [
            p_float, c_int, c_int, c_int, c_int, c_int, p_float
        ]
        lib.sireikon_cuda_scatter_head.restype = c_int
        lib.sireikon_cuda_concat_heads.argtypes = [
            p_float, c_int, c_int, c_int, c_int, p_float
        ]
        lib.sireikon_cuda_concat_heads.restype = c_int
        lib.sireikon_cuda_split_head_grad.argtypes = [
            p_float, c_int, c_int, c_int, c_int, c_int, p_float
        ]
        lib.sireikon_cuda_split_head_grad.restype = c_int
        lib.sireikon_cuda_rope_forward.argtypes = [
            p_float, c_int, c_int, c_int, c_int, c_float, p_float
        ]
        lib.sireikon_cuda_rope_forward.restype = c_int
        lib.sireikon_cuda_rope_backward.argtypes = [
            p_float, c_int, c_int, c_int, c_int, c_float, p_float
        ]
        lib.sireikon_cuda_rope_backward.restype = c_int

        lib.sireikon_cuda_attention_forward.argtypes = [
            p_float, p_float, p_float,
            c_int, c_int, c_int, c_int,
            p_int, c_int,
            p_float, p_float,
        ]
        lib.sireikon_cuda_attention_forward.restype = c_int
        lib.sireikon_cuda_attention_backward.argtypes = [
            p_float, p_float, p_float, p_float, p_float,
            c_int, c_int, c_int, c_int,
            p_float, p_float, p_float,
        ]
        lib.sireikon_cuda_attention_backward.restype = c_int

        lib.sireikon_cuda_layernorm_forward.argtypes = [
            p_float, p_float, p_float,
            c_int, c_int, c_float, c_int,
            p_float, p_float, p_float,
        ]
        lib.sireikon_cuda_layernorm_forward.restype = c_int
        lib.sireikon_cuda_layernorm_backward.argtypes = [
            p_float, p_float, p_float, p_float, p_float,
            c_int, c_int, c_int,
            p_float, p_float, p_float,
        ]
        lib.sireikon_cuda_layernorm_backward.restype = c_int

        lib.sireikon_cuda_embedding_forward.argtypes = [
            p_float, p_int, c_int, c_int, c_int, p_float,
        ]
        lib.sireikon_cuda_embedding_forward.restype = c_int
        lib.sireikon_cuda_embedding_backward.argtypes = [
            p_float, p_int, c_int, c_int, c_int, c_int, p_float,
        ]
        lib.sireikon_cuda_embedding_backward.restype = c_int

        lib.sireikon_cuda_cross_entropy_forward.argtypes = [
            p_float, p_int, c_int, c_int, c_int, c_float,
            p_float, p_float, p_int,
        ]
        lib.sireikon_cuda_cross_entropy_forward.restype = c_int
        lib.sireikon_cuda_cross_entropy_backward.argtypes = [
            p_float, p_int, p_int, p_float,
            c_int, c_int, c_float, c_float, c_int, c_int,
            p_float,
        ]
        lib.sireikon_cuda_cross_entropy_backward.restype = c_int

        lib.sireikon_cuda_adamw.argtypes = [
            p_float, p_float, p_float, p_float, c_int,
            c_float, c_float, c_float, c_float, c_float,
            c_float, c_float, c_float,
            p_float, p_float, p_float,
        ]
        lib.sireikon_cuda_adamw.restype = c_int

    def configure(self, mode="auto", device_index=0, strict=True):
        mode = str(mode).lower()
        if mode not in ("auto", "cpu", "cuda"):
            raise ValueError("device must be auto, cpu, or cuda")
        self.requested = mode
        self.device_index = int(device_index)

        if mode == "cpu":
            self.active = "cpu"
            return self.status()

        if self.library is None:
            self.active = "cpu"
            if mode == "cuda" and strict:
                raise RuntimeError(
                    "CUDA requested but SireSoft-IKON CUDA backend is unavailable: "
                    + str(self.load_error)
                )
            return self.status()

        count = ctypes.c_int(0)
        code = self.library.sireikon_cuda_device_count(ctypes.byref(count))
        if code != 0 or count.value <= 0:
            self.active = "cpu"
            if mode == "cuda" and strict:
                self._raise("CUDA device discovery")
            return self.status()

        if self.device_index < 0 or self.device_index >= count.value:
            self.active = "cpu"
            if mode == "cuda" and strict:
                raise RuntimeError(
                    "CUDA device index " + str(self.device_index)
                    + " is out of range for " + str(count.value) + " device(s)"
                )
            return self.status()

        code = self.library.sireikon_cuda_set_device(self.device_index)
        if code != 0:
            self.active = "cpu"
            if mode == "cuda" and strict:
                self._raise("CUDA device selection")
            return self.status()

        self.active = "cuda"
        return self.status()

    def enabled(self):
        return self.active == "cuda" and self.library is not None

    def status(self):
        return {
            "requested": self.requested,
            "active": self.active,
            "device_index": self.device_index,
            "library": self.library_path,
            "load_error": self.load_error,
            "calls": dict(self.calls),
        }

    def reset_call_stats(self):
        self.calls = {}

    def _record(self, name):
        self.calls[name] = self.calls.get(name, 0) + 1

    def _last_error(self):
        if self.library is None:
            return self.load_error or "CUDA backend unavailable"
        raw = self.library.sireikon_cuda_last_error()
        if raw:
            try:
                return raw.decode("utf-8", errors="replace")
            except Exception:
                return str(raw)
        return "unknown CUDA backend error"

    def _raise(self, operation):
        raise RuntimeError(operation + " failed: " + self._last_error())

    def _check(self, code, operation):
        if int(code) != 0:
            self._raise(operation)

    def _float_array(self, values):
        values = [float(value) for value in values]
        array_type = ctypes.c_float * len(values)
        return array_type(*values)

    def _int_array(self, values):
        values = [int(value) for value in values]
        array_type = ctypes.c_int * len(values)
        return array_type(*values)

    def _empty_float_array(self, size):
        return (ctypes.c_float * int(size))()

    def _to_list(self, array, size):
        return [float(array[index]) for index in range(int(size))]

    def binary_broadcast(self, left, left_shape, right, right_shape, output_shape, mode):
        self._record("binary_broadcast")
        left_a = self._float_array(left)
        right_a = self._float_array(right)
        left_s = self._int_array(left_shape)
        right_s = self._int_array(right_shape)
        out_s = self._int_array(output_shape)
        size = 1
        for dim in output_shape:
            size *= int(dim)
        out = self._empty_float_array(size)
        code = self.library.sireikon_cuda_binary_broadcast(
            left_a, left_s, len(left_shape),
            right_a, right_s, len(right_shape),
            out_s, len(output_shape), self._MODE_CODES[mode], out,
        )
        self._check(code, "CUDA binary broadcast")
        return self._to_list(out, size)

    def unary(self, values, mode):
        self._record("unary_" + mode)
        src = self._float_array(values)
        out = self._empty_float_array(len(values))
        code = self.library.sireikon_cuda_unary(
            src, len(values), self._UNARY_CODES[mode], out
        )
        self._check(code, "CUDA unary " + mode)
        return self._to_list(out, len(values))

    def power(self, values, exponent):
        self._record("power")
        src = self._float_array(values)
        out = self._empty_float_array(len(values))
        code = self.library.sireikon_cuda_power(
            src, len(values), ctypes.c_float(float(exponent)), out
        )
        self._check(code, "CUDA power")
        return self._to_list(out, len(values))

    def activation_backward(self, source, output, upstream, mode, parameter=0.0):
        self._record("activation_backward_" + mode)
        mode_codes = {
            "exp": 0, "log": 1, "tanh": 2, "sigmoid": 3,
            "relu": 4, "power": 5,
        }
        src = self._float_array(source)
        out_values = self._float_array(output)
        up = self._float_array(upstream)
        grad = self._empty_float_array(len(source))
        code = self.library.sireikon_cuda_activation_backward(
            src, out_values, up, len(source), mode_codes[mode],
            float(parameter), grad,
        )
        self._check(code, "CUDA activation backward " + mode)
        return self._to_list(grad, len(source))

    def sum(self, values):
        self._record("sum")
        src = self._float_array(values)
        out = ctypes.c_float(0.0)
        code = self.library.sireikon_cuda_sum(src, len(values), ctypes.byref(out))
        self._check(code, "CUDA sum")
        return float(out.value)

    def sum_squares(self, values):
        self._record("sum_squares")
        src = self._float_array(values)
        out = ctypes.c_float(0.0)
        code = self.library.sireikon_cuda_sum_squares(src, len(values), ctypes.byref(out))
        self._check(code, "CUDA sum squares")
        return float(out.value)

    def scale(self, values, scale):
        self._record("scale")
        src = self._float_array(values)
        out = self._empty_float_array(len(values))
        code = self.library.sireikon_cuda_scale(src, len(values), float(scale), out)
        self._check(code, "CUDA scale")
        return self._to_list(out, len(values))

    def transpose2d(self, values, rows, cols):
        self._record("transpose2d")
        src = self._float_array(values)
        out = self._empty_float_array(len(values))
        code = self.library.sireikon_cuda_transpose2d(src, rows, cols, out)
        self._check(code, "CUDA transpose2d")
        return self._to_list(out, len(values))

    def matmul(self, left, right, rows, inner, cols):
        self._record("matmul")
        a = self._float_array(left)
        b = self._float_array(right)
        out = self._empty_float_array(rows * cols)
        code = self.library.sireikon_cuda_matmul(a, b, rows, inner, cols, out)
        self._check(code, "CUDA matmul")
        return self._to_list(out, rows * cols)

    def extract_head(self, source, batch, sequence, d_model, head_start, head_dim):
        self._record("extract_head")
        src = self._float_array(source)
        out = self._empty_float_array(batch * sequence * head_dim)
        code = self.library.sireikon_cuda_extract_head(
            src, batch, sequence, d_model, head_start, head_dim, out
        )
        self._check(code, "CUDA extract head")
        return self._to_list(out, batch * sequence * head_dim)

    def scatter_head(self, upstream, batch, sequence, d_model, head_start, head_dim):
        self._record("scatter_head")
        up = self._float_array(upstream)
        out = self._empty_float_array(batch * sequence * d_model)
        code = self.library.sireikon_cuda_scatter_head(
            up, batch, sequence, d_model, head_start, head_dim, out
        )
        self._check(code, "CUDA scatter head")
        return self._to_list(out, batch * sequence * d_model)

    def concat_heads(self, flat_heads, batch, sequence, num_heads, head_dim):
        self._record("concat_heads")
        src = self._float_array(flat_heads)
        d_model = num_heads * head_dim
        out = self._empty_float_array(batch * sequence * d_model)
        code = self.library.sireikon_cuda_concat_heads(
            src, batch, sequence, num_heads, head_dim, out
        )
        self._check(code, "CUDA concat heads")
        return self._to_list(out, batch * sequence * d_model)

    def split_head_grad(self, upstream, batch, sequence, num_heads, head_dim, head_index):
        self._record("split_head_grad")
        up = self._float_array(upstream)
        out = self._empty_float_array(batch * sequence * head_dim)
        code = self.library.sireikon_cuda_split_head_grad(
            up, batch, sequence, num_heads, head_dim, head_index, out
        )
        self._check(code, "CUDA split head gradient")
        return self._to_list(out, batch * sequence * head_dim)

    def rope_forward(self, source, batch, sequence, head_dim, position_offset, base):
        self._record("rope_forward")
        src = self._float_array(source)
        out = self._empty_float_array(len(source))
        code = self.library.sireikon_cuda_rope_forward(
            src, batch, sequence, head_dim, position_offset, float(base), out
        )
        self._check(code, "CUDA RoPE forward")
        return self._to_list(out, len(source))

    def rope_backward(self, upstream, batch, sequence, head_dim, position_offset, base):
        self._record("rope_backward")
        up = self._float_array(upstream)
        out = self._empty_float_array(len(upstream))
        code = self.library.sireikon_cuda_rope_backward(
            up, batch, sequence, head_dim, position_offset, float(base), out
        )
        self._check(code, "CUDA RoPE backward")
        return self._to_list(out, len(upstream))

    def attention_forward(self, q, k, v, batch, query_length, key_length, dimension, mask_values=None, causal=False):
        self._record("attention_forward")
        q_a = self._float_array(q)
        k_a = self._float_array(k)
        v_a = self._float_array(v)
        if mask_values is None:
            mask_a = None
            has_mask = 0
        else:
            mask_a = self._int_array(mask_values)
            has_mask = 1
        out = self._empty_float_array(batch * query_length * dimension)
        weights = self._empty_float_array(batch * query_length * key_length)
        code = self.library.sireikon_cuda_attention_forward(
            q_a, k_a, v_a,
            batch, query_length, key_length, dimension,
            mask_a, has_mask if has_mask else (-1 if causal else 0),
            out, weights,
        )
        self._check(code, "CUDA attention forward")
        return (
            self._to_list(out, batch * query_length * dimension),
            self._to_list(weights, batch * query_length * key_length),
        )

    def attention_backward(self, q, k, v, weights, upstream, batch, query_length, key_length, dimension):
        self._record("attention_backward")
        q_a = self._float_array(q)
        k_a = self._float_array(k)
        v_a = self._float_array(v)
        w_a = self._float_array(weights)
        up_a = self._float_array(upstream)
        dq = self._empty_float_array(len(q))
        dk = self._empty_float_array(len(k))
        dv = self._empty_float_array(len(v))
        code = self.library.sireikon_cuda_attention_backward(
            q_a, k_a, v_a, w_a, up_a,
            batch, query_length, key_length, dimension,
            dq, dk, dv,
        )
        self._check(code, "CUDA attention backward")
        return self._to_list(dq, len(q)), self._to_list(dk, len(k)), self._to_list(dv, len(v))

    def layernorm_forward(self, values, gamma, beta, rows, width, epsilon, affine):
        self._record("layernorm_forward")
        x = self._float_array(values)
        gamma_a = self._float_array(gamma) if affine else None
        beta_a = self._float_array(beta) if affine else None
        out = self._empty_float_array(len(values))
        normalized = self._empty_float_array(len(values))
        inv_stds = self._empty_float_array(rows)
        code = self.library.sireikon_cuda_layernorm_forward(
            x, gamma_a, beta_a, rows, width, float(epsilon), 1 if affine else 0,
            out, normalized, inv_stds,
        )
        self._check(code, "CUDA layernorm forward")
        return self._to_list(out, len(values)), self._to_list(normalized, len(values)), self._to_list(inv_stds, rows)

    def layernorm_backward(self, upstream, normalized, inv_stds, gamma, rows, width, affine):
        self._record("layernorm_backward")
        up = self._float_array(upstream)
        norm = self._float_array(normalized)
        inv = self._float_array(inv_stds)
        gamma_a = self._float_array(gamma) if affine else None
        dx = self._empty_float_array(rows * width)
        dgamma = self._empty_float_array(width)
        dbeta = self._empty_float_array(width)
        code = self.library.sireikon_cuda_layernorm_backward(
            up, norm, inv, gamma_a, None,
            rows, width, 1 if affine else 0,
            dx, dgamma, dbeta,
        )
        self._check(code, "CUDA layernorm backward")
        return self._to_list(dx, rows * width), self._to_list(dgamma, width), self._to_list(dbeta, width)

    def embedding_forward(self, weights, token_ids, num_embeddings, embedding_dim):
        self._record("embedding_forward")
        w = self._float_array(weights)
        ids = self._int_array(token_ids)
        out = self._empty_float_array(len(token_ids) * embedding_dim)
        code = self.library.sireikon_cuda_embedding_forward(
            w, ids, len(token_ids), num_embeddings, embedding_dim, out
        )
        self._check(code, "CUDA embedding forward")
        return self._to_list(out, len(token_ids) * embedding_dim)

    def embedding_backward(self, upstream, token_ids, num_embeddings, embedding_dim, padding_idx):
        self._record("embedding_backward")
        up = self._float_array(upstream)
        ids = self._int_array(token_ids)
        out = self._empty_float_array(num_embeddings * embedding_dim)
        code = self.library.sireikon_cuda_embedding_backward(
            up, ids, len(token_ids), num_embeddings, embedding_dim,
            int(padding_idx), out,
        )
        self._check(code, "CUDA embedding backward")
        return self._to_list(out, num_embeddings * embedding_dim)

    def cross_entropy_forward(self, logits, targets, rows, classes, ignore_index, smoothing):
        self._record("cross_entropy_forward")
        x = self._float_array(logits)
        t = self._int_array(targets)
        probs = self._empty_float_array(len(logits))
        losses = self._empty_float_array(rows)
        active = (ctypes.c_int * rows)()
        code = self.library.sireikon_cuda_cross_entropy_forward(
            x, t, rows, classes, int(ignore_index), float(smoothing),
            probs, losses, active,
        )
        self._check(code, "CUDA cross entropy forward")
        return self._to_list(probs, len(logits)), self._to_list(losses, rows), [int(active[i]) for i in range(rows)]

    def cross_entropy_backward(self, probabilities, targets, active, upstream_rows, rows, classes, smoothing, active_count, reduction):
        self._record("cross_entropy_backward")
        probs = self._float_array(probabilities)
        t = self._int_array(targets)
        act = self._int_array(active)
        up = self._float_array(upstream_rows)
        gradient = self._empty_float_array(rows * classes)
        reduction_code = {"none": 0, "sum": 1, "mean": 2}[reduction]
        code = self.library.sireikon_cuda_cross_entropy_backward(
            probs, t, act, up,
            rows, classes, float(smoothing), float(active_count), reduction_code, 0,
            gradient,
        )
        self._check(code, "CUDA cross entropy backward")
        return self._to_list(gradient, rows * classes)

    def adamw(self, values, gradients, first, second, learning_rate, beta1, beta2, epsilon, weight_decay, scale, bias_correction1, bias_correction2):
        self._record("adamw")
        v = self._float_array(values)
        g = self._float_array(gradients)
        m = self._float_array(first)
        s = self._float_array(second)
        out_v = self._empty_float_array(len(values))
        out_m = self._empty_float_array(len(values))
        out_s = self._empty_float_array(len(values))
        code = self.library.sireikon_cuda_adamw(
            v, g, m, s, len(values),
            float(learning_rate), float(beta1), float(beta2), float(epsilon), float(weight_decay),
            float(scale), float(bias_correction1), float(bias_correction2),
            out_v, out_m, out_s,
        )
        self._check(code, "CUDA AdamW")
        return self._to_list(out_v, len(values)), self._to_list(out_m, len(values)), self._to_list(out_s, len(values))


GPU_BACKEND = CudaBackend()
