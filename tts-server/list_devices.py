import json
import sounddevice as sd


def main() -> None:
    devices = sd.query_devices()
    default = sd.default.device
    print("default:", default)
    mapping = [(i, d.get("name", "?")) for i, d in enumerate(devices)]
    print(json.dumps(mapping, ensure_ascii=False))


if __name__ == "__main__":
    main()


