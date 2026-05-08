"""
find_polar.py — Quét và tìm thiết bị Polar H10
Fix: dùng BleakScanner.discover() đúng cách với callback,
     thêm timeout, hiển thị RSSI, hỗ trợ Raspberry Pi 5
"""

import asyncio
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData


def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    """Callback gọi ngay khi phát hiện thiết bị mới."""
    name = device.name or advertisement_data.local_name or ""
    if "Polar" in name:
        rssi = advertisement_data.rssi
        signal_strength = (
            "Rất tốt" if rssi > -60 else
            "Tốt"    if rssi > -70 else
            "Trung bình" if rssi > -80 else
            "Yếu"
        )
        print(f"  ✓ Tìm thấy: {name}")
        print(f"    MAC Address : {device.address}")
        print(f"    RSSI        : {rssi} dBm ({signal_strength})")
        print(f"    Services    : {list(advertisement_data.service_uuids)[:3]}")
        print()


async def scan(timeout: float = 10.0):
    print("=" * 55)
    print("  POLAR H10 — BLE SCANNER")
    print("=" * 55)
    print(f"Đang quét {timeout} giây...")
    print("Hãy đảm bảo Polar H10 đã đeo vào ngực (đèn nhấp nháy xanh)\n")

    # Dùng callback để hiển thị thiết bị ngay khi tìm thấy
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()

    # Lọc tất cả Polar devices từ discovered
    all_devices = scanner.discovered_devices_and_advertisement_data
    polar_devices = [
        (dev, adv) for dev, adv in all_devices.values()
        if dev.name and "Polar" in dev.name
    ]

    print("=" * 55)
    if polar_devices:
        print(f"Tổng cộng tìm thấy {len(polar_devices)} thiết bị Polar:")
        for dev, adv in polar_devices:
            print(f"  → {dev.name}  |  {dev.address}")
        print("\nSao chép địa chỉ MAC vào biến POLAR_ADDRESS trong các script khác.")
    else:
        print("Không tìm thấy thiết bị Polar nào. Kiểm tra:")
        print("  1. Đã đeo đúng cách (điện cực tiếp xúc da)?")
        print("  2. Đèn trên thiết bị có nhấp nháy xanh không?")
        print("  3. BLE adapter của máy có hoạt động không?")
        print("     → Thử: hciconfig hci0  (chỉ Linux/Raspberry Pi)")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(scan(timeout=10.0))