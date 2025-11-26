
import sys
from pathlib import Path

import onnx
from onnxconverter_common import float16


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python convert_to_fp16.py <src.onnx> <dst.onnx>")
        return 2

    src_path = Path(sys.argv[1])
    dst_path = Path(sys.argv[2])

    if not src_path.exists():
        print(f"Source not found: {src_path}")
        return 1

    # Load with external data support to avoid loading all tensor bytes into memory
    model = onnx.load(str(src_path), load_external_data=True)
    # Keep IO types and avoid converting ops that expect float outputs (e.g., Cast)
    model_fp16 = float16.convert_float_to_float16(
        model,
        keep_io_types=True,
        op_block_list=["Cast"],
    )
    # Save as external data to keep the main .onnx small and reduce memory pressure
    onnx.save_model(
        model_fp16,
        str(dst_path),
        save_as_external_data=True,
        all_tensors_to_one_file=True,
        convert_attribute=False,
        size_threshold=1024,
    )
    print(f"Wrote {dst_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


