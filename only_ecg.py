"""
data_collector_ecg_only.py
====================
Thu thập DUY NHẤT dữ liệu ECG thô từ Polar H10
- ECG (Tần số: 130 Hz)

Output:
  polar_data/
    ecg_data_YYYYMMDD_HHMMSS.csv   ← Chỉ chứa dữ liệu ECG

Cách dùng:
  python data_collector_ecg_only.py
  
  Nhấn Ctrl+C để dừng và lưu
"""

import asyncio
import time
import csv
import threading
from datetime import datetime
from pathlib import Path

from bleak import BleakClient

# ════════════════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════════════════
POLAR_ADDRESS = "24:AC:AC:13:EB:86"

# Characteristics dành riêng cho dữ liệu PMD (ECG)
PMD_CONTROL = "fb005c81-02e7-f387-1cad-8acd2d8df0c8"   # Gửi lệnh điều khiển
PMD_DATA = "fb005c82-02e7-f387-1cad-8acd2d8df0c8"      # Nhận luồng dữ liệu ECG

# Lệnh bắt đầu thu ECG (Cấu hình mặc định: 130 Hz)
ECG_START_CMD = bytearray([
    0x02, 0x00, 0x00, 0x01,
    0x82, 0x00, 0x01, 0x01, 0x0E, 0x00
])

# Output
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = Path("polar_data")
output_dir.mkdir(exist_ok=True)

ecg_csv_path = output_dir / f"ecg_data_{session_id}.csv"

# ════════════════════════════════════════════════════════════════
#  GLOBAL STATE
# ════════════════════════════════════════════════════════════════
is_running = True
ecg_count = 0
lock = threading.Lock()

# ════════════════════════════════════════════════════════════════
#  CSV SETUP (Chỉ giữ lại các cột cho ECG)
# ════════════════════════════════════════════════════════════════
ecg_csv = open(ecg_csv_path, "w", newline="", encoding="utf-8")
ecg_writer = csv.writer(ecg_csv)
ecg_writer.writerow(["timestamp_ns_polar", "timestamp_unix", "timestamp", "ecg_uv"])
ecg_csv.flush()

# ════════════════════════════════════════════════════════════════
#  PARSER ECG
# ════════════════════════════════════════════════════════════════
def parse_ecg_data(data: bytes) -> list:
    """
    Parse ECG data từ PMD_DATA characteristic
    
    Polar PMD Header (10 bytes):
      - byte 0: type (0x00 = ECG)
      - bytes 1-8: timestamp (uint64 little-endian, nanoseconds)
      - byte 9: frame_type (unused)
    
    ECG Data: 3 bytes per sample (24-bit signed little-endian, µV)
    """
    # Kiểm tra độ dài header
    if len(data) < 10:
        return []
    
    # Kiểm tra loại dữ liệu
    if data[0] != 0x00:
        return []
    
    samples = []
    try:
        # Lấy timestamp từ header (bytes 1-8, little-endian uint64, nanoseconds)
        timestamp_ns = int.from_bytes(data[1:9], byteorder='little', signed=False)
        
        # Bắt đầu đọc dữ liệu ECG từ offset 10
        offset = 10
        sample_index = 0
        ecg_sample_interval_ns = int((1 / 130) * 1e9)  # 130 Hz → ~7692308 ns per sample
        
        while offset + 2 < len(data):
            # Đọc 3 bytes (24-bit signed little-endian), đơn vị µV
            raw_bytes = data[offset:offset + 3]
            ecg_uv = int.from_bytes(raw_bytes, byteorder='little', signed=True)
            
            # Tính timestamp cho mỗi sample
            sample_timestamp_ns = timestamp_ns + (sample_index * ecg_sample_interval_ns)
            sample_timestamp_unix = sample_timestamp_ns / 1e9
            ts_str = datetime.fromtimestamp(sample_timestamp_unix).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            samples.append([sample_timestamp_ns, sample_timestamp_unix, ts_str, ecg_uv])
            offset += 3
            sample_index += 1
    except Exception as e:
        print(f"[ECG Parse Error] {e}")
    
    return samples

# ════════════════════════════════════════════════════════════════
#  BLE CALLBACK
# ════════════════════════════════════════════════════════════════
def ecg_callback(sender, data: bytearray):
    """Callback xử lý và ghi dữ liệu ECG"""
    global ecg_count
    try:
        samples = parse_ecg_data(bytes(data))
        for sample in samples:
            ts_ns_polar, ts_unix, ts_str, ecg_uv = sample
            ecg_writer.writerow([f"{ts_ns_polar}", f"{ts_unix:.6f}", ts_str, f"{ecg_uv}"])
            with lock:
                ecg_count += 1
        ecg_csv.flush()
    except Exception as e:
        print(f"[ECG Callback Error] {e}")

# ════════════════════════════════════════════════════════════════
#  DISPLAY STATS (Chỉ hiển thị ECG)
# ════════════════════════════════════════════════════════════════
def display_stats():
    start = time.time()
    while is_running:
        time.sleep(1)
        elapsed = int(time.time() - start)
        with lock:
            ecg_samples = ecg_count
        
        ecg_rate = ecg_samples / max(elapsed, 1)
        
        print(f"\033[2J\033[H", end="")
        print("=" * 60)
        print("  POLAR H10  —  ONLY ECG COLLECTOR")
        print("=" * 60)
        print(f"  Runtime: {elapsed // 60:02d}:{elapsed % 60:02d}")
        print()
        print(f"  ECG samples: {ecg_samples:8,}  ({ecg_rate:.1f} Hz)")
        print()
        print("  Press Ctrl+C to stop and save")
        print("=" * 60)
        print(f"  📄 {ecg_csv_path.name}")
        print("=" * 60)

# ════════════════════════════════════════════════════════════════
#  SERVICE DISCOVERY
# ════════════════════════════════════════════════════════════════
async def discover_services(client):
    """Log all available services and characteristics"""
    print("\n  Discovering services...\n")
    found_pmd_control = False
    found_pmd_data = False
    
    for service in client.services:
        if "fb005c" in service.uuid.lower():  # Polar PMD Service
            print(f"  📡 Found PMD Service: {service.uuid}")
            for char in service.characteristics:
                char_uuid = char.uuid.lower()
                print(f"     - {char_uuid} ({', '.join(char.properties)})")
                if char_uuid == PMD_CONTROL.lower():
                    found_pmd_control = True
                if char_uuid == PMD_DATA.lower():
                    found_pmd_data = True
    
    if found_pmd_control and found_pmd_data:
        print("  ✓ PMD service complete\n")
        return True
    else:
        print(f"  ❌ PMD Service incomplete:")
        print(f"     PMD_CONTROL found: {found_pmd_control}")
        print(f"     PMD_DATA found: {found_pmd_data}\n")
        return False

# ════════════════════════════════════════════════════════════════
#  BLE ASYNC
# ════════════════════════════════════════════════════════════════
async def run_ble():
    global is_running
    retry_count = 0
    max_retries = 5
    
    while is_running and retry_count < max_retries:
        try:
            print(f"Connecting to {POLAR_ADDRESS}... (attempt {retry_count + 1}/{max_retries})")
            async with BleakClient(POLAR_ADDRESS, timeout=20) as client:
                print("✓ Connected!")
                
                # Discover and verify services
                services_ok = await discover_services(client)
                
                if not services_ok:
                    print("⚠  Required services not available")
                    print("  Disconnecting and retrying...\n")
                    retry_count += 1
                    await asyncio.sleep(3)
                    continue
                
                # Try to enable ECG
                try:
                    print("  Starting ECG receiver...")
                    await client.write_gatt_char(PMD_CONTROL, ECG_START_CMD, response=True)
                    await client.start_notify(PMD_DATA, ecg_callback)
                    print("✓ ECG enabled\n")
                    retry_count = 0  # Reset retry count on success
                except Exception as e:
                    print(f"⚠  Failed to enable ECG: {e}")
                    print(f"  Retrying in 5s...\n")
                    retry_count += 1
                    await asyncio.sleep(5)
                    continue
                
                while is_running and client.is_connected:
                    await asyncio.sleep(0.5)
        
        except asyncio.TimeoutError:
            print(f"⚠  Connection timeout")
            print(f"  Retrying in 5s...\n")
            retry_count += 1
            await asyncio.sleep(5)
        except Exception as e:
            if is_running:
                print(f"⚠  Connection error: {e}")
                print(f"  Retrying in 5s...\n")
                retry_count += 1
                await asyncio.sleep(5)
            else:
                break
    
    if retry_count >= max_retries:
        print(f"\n❌ Failed to connect after {max_retries} attempts")
        print("   Please verify:")
        print("   1. Polar H10 is powered on (check LED)")
        print("   2. Polar H10 is within range")
        print("   3. MAC address is correct: {POLAR_ADDRESS}")
        print("   4. Run 'python scan_uuids.py' to debug services\n")
        is_running = False

def run_ble_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_ble())
    except Exception as e:
        print(f"BLE Error: {e}")
    finally:
        loop.close()

# ════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  POLAR H10  —  ECG ONLY COLLECTOR")
    print(f"  Session: {session_id}")
    print("=" * 60)
    print(f"\nOutput file: {ecg_csv_path}")
    print(f"\nStarting in 3s...\n")
    time.sleep(3)
    
    threads = [
        threading.Thread(target=run_ble_thread, daemon=True, name="BLE"),
        threading.Thread(target=display_stats, daemon=True, name="Display"),
    ]
    
    for t in threads:
        t.start()
    
    try:
        while is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        is_running = False
        time.sleep(1)
    
    ecg_csv.close()
    
    # In báo cáo cuối cùng
    print("\n" + "=" * 60)
    print("  SESSION SAVED")
    print("=" * 60)
    print(f"✓ File created: {ecg_csv_path}")
    print(f"✓ Total ECG samples collected: {ecg_count:,}")
    print("=" * 60)