"""
diagnose_pmd.py — Diagnose why PMD service is not available
"""

import asyncio
import time
from bleak import BleakClient, BleakScanner

POLAR_ADDRESS = "24:AC:AC:13:EB:86"

async def main():
    print("=" * 70)
    print("  POLAR H10 — PMD SERVICE DIAGNOSTIC")
    print("=" * 70)
    
    print("\n[1/2] Attempting direct connection...")
    try:
        async with BleakClient(POLAR_ADDRESS, timeout=20) as client:
            print("✓ Connected!")
            
            # Check services
            print("\n[2/2] Checking available services...")
            services_list = list(client.services)
            print(f"Total services found: {len(services_list)}")
            
            has_pmd = False
            has_hr = False
            pmd_characteristics = {}
            
            for service in services_list:
                uuid = service.uuid.lower()
                if "fb005c" in uuid:
                    has_pmd = True
                    print(f"\n✓ Found PMD Service: {service.uuid}")
                    for char in service.characteristics:
                        char_uuid = char.uuid.lower()
                        print(f"  - {char_uuid}")
                        pmd_characteristics[char_uuid] = char
                
                if uuid == "0000180d-0000-1000-8000-00805f9b34fb":
                    has_hr = True
                    print(f"\n✓ Found Heart Rate Service: {service.uuid}")
            
            # Diagnosis
            print("\n" + "=" * 70)
            print("DIAGNOSIS:")
            print("=" * 70)
            
            if has_pmd:
                print("✓ PMD Service is AVAILABLE")
                print("  → ECG/ACC streaming should work")
                print("\n✓ Try running: python only_ecg.py")
            else:
                print("❌ PMD Service is NOT AVAILABLE")
                print("\nRoot Cause Analysis:")
                print("  The Polar H10 is in BASIC MODE (only generic BLE services)")
                print("  It does NOT expose the PMD (Proprietary Medical Data) service")
                print("  which is needed for ECG and ACC streaming.")
                print("\nPossible Causes:")
                print("  1. Device firmware needs initialization via Polar mobile app")
                print("  2. Device is in low-power/locked mode")
                print("  3. BLE connection state needs reset")
                print("\nSOLUTIONS TO TRY:")
                print("  ─────────────────")
                print("\n  Option 1: Initialize via Polar App (RECOMMENDED)")
                print("    1. Download 'Polar Beat' or 'Polar Flow' app on phone")
                print("    2. Pair Polar H10 to the app")
                print("    3. Sync the device through the app")
                print("    4. Then reconnect here")
                print("\n  Option 2: Hard Reset the Device")
                print("    1. Remove Polar H10 from your chest")
                print("    2. Forget the device in Windows Bluetooth settings")
                print("    3. Power off Polar H10 (if possible)")
                print("    4. Wait 30 seconds")
                print("    5. Re-pair the device")
                print("\n  Option 3: Check Device Status")
                print("    • Is the LED blinking BLUE? (indicates BLE ready)")
                print("    • Is the battery low? (connect to charger)")
                print("    • Firmware version: unknown (check via Polar app)")
            
            if has_hr:
                print("\n✓ Heart Rate Service is AVAILABLE")
                print("  → HR measurement without ECG is possible")
    
    except asyncio.TimeoutError:
        print("❌ Connection timed out (20 seconds)")
        print("\nTroubleshooting:")
        print("  • Is Polar H10 powered ON? (check LED)")
        print("  • Is MAC address correct? (current: {POLAR_ADDRESS})")
        print("  • Is Polar H10 within 10 meters?")
        print("  • Try: python find_polar.py")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  • Forget the device in Windows Bluetooth settings")
        print("  • Re-pair the Polar H10")
        print("  • Try: python find_polar.py")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled")
