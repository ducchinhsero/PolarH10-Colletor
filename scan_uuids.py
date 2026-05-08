"""
scan_uuids.py — Liệt kê toàn bộ services và characteristics của Polar H10
Fix: thêm đọc giá trị, hiển thị properties rõ ràng hơn,
     highlight các UUID quan trọng cho ECG và HR
"""

import asyncio
from bleak import BleakClient

# ── Thay MAC address của bạn vào đây ────────────────────────────
POLAR_ADDRESS = "24:AC:AC:13:EB:86"

# UUID quan trọng cần highlight
IMPORTANT_UUIDS = {
    "00002a37-0000-1000-8000-00805f9b34fb": "❤️  HEART RATE MEASUREMENT (HR + RR intervals)",
    "fb005c81-02e7-f387-1cad-8acd2d8df0c8": "🔧 PMD CONTROL (write lệnh bắt đầu ECG/ACC)",
    "fb005c82-02e7-f387-1cad-8acd2d8df0c8": "📡 PMD DATA (nhận ECG 130Hz + ACC 25Hz)",
    "00002a19-0000-1000-8000-00805f9b34fb": "🔋 BATTERY LEVEL",
    "00002a00-0000-1000-8000-00805f9b34fb": "📛 DEVICE NAME",
    "00002a29-0000-1000-8000-00805f9b34fb": "🏭 MANUFACTURER NAME",
    "00002a24-0000-1000-8000-00805f9b34fb": "🔢 MODEL NUMBER",
    "00002a27-0000-1000-8000-00805f9b34fb": "💾 HARDWARE REVISION",
    "00002a26-0000-1000-8000-00805f9b34fb": "📦 FIRMWARE REVISION",
}


async def main():
    print(f"Đang kết nối tới {POLAR_ADDRESS}...")

    async with BleakClient(POLAR_ADDRESS, timeout=15) as client:
        if not client.is_connected:
            print("❌ Kết nối thất bại!")
            return

        print(f"✓ Đã kết nối\n")
        print("=" * 80)
        print("  SERVICES & CHARACTERISTICS")
        print("=" * 80)

        for service in client.services:
            print(f"\n┌─ SERVICE: {service.uuid}")
            if service.description and service.description != "Unknown":
                print(f"│  Mô tả: {service.description}")

            for i, char in enumerate(service.characteristics):
                is_last   = (i == len(service.characteristics) - 1)
                prefix    = "└──" if is_last else "├──"
                sub_prefix= "    " if is_last else "│   "

                uuid  = char.uuid
                props = ", ".join(char.properties)

                # Highlight UUID quan trọng
                label = IMPORTANT_UUIDS.get(uuid, "")

                print(f"│  {prefix} {uuid}")
                if label:
                    print(f"│  {sub_prefix}  {label}")
                if char.description and char.description != "Unknown":
                    print(f"│  {sub_prefix}  Mô tả  : {char.description}")
                print(f"│  {sub_prefix}  Quyền  : {props}")

                # Đọc giá trị nếu có quyền read
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        # Cố decode utf-8, nếu không thì hex
                        try:
                            decoded = value.decode("utf-8").strip()
                            print(f"│  {sub_prefix}  Giá trị: '{decoded}'")
                        except UnicodeDecodeError:
                            print(f"│  {sub_prefix}  Giá trị: {value.hex()} (hex)")
                    except Exception:
                        pass  # Một số char không đọc được khi không active

        print("\n" + "=" * 80)
        print("  UUID QUAN TRỌNG CẦN GHI NHỚ")
        print("=" * 80)
        for uuid, label in IMPORTANT_UUIDS.items():
            print(f"  {label}")
            print(f"  → {uuid}\n")


if __name__ == "__main__":
    asyncio.run(main())