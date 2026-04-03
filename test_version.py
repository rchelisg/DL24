# Test script to verify version incrementing logic

def test_version_increment():
    # Test cases for version incrementing
    test_cases = [
        ("0.1.98", "0.1.99"),  # Normal increment
        ("0.1.99", "0.2.00"),  # Patch reaches 99, increment minor
        ("0.2.00", "0.2.01"),  # Normal increment after reset
        ("0.9.99", "1.0.00"),  # Edge case: minor reaches 99
    ]
    
    print("Testing version incrementing logic...")
    
    for current_version, expected_version in test_cases:
        # Split version into components
        major, minor, patch = map(int, current_version.split('.'))
        
        # Increment patch
        patch += 1
        
        # If patch reaches 99, reset to 00 and increment minor
        if patch > 99:
            patch = 0
            minor += 1
            # If minor reaches 99, reset to 0 and increment major
            if minor > 99:
                minor = 0
                major += 1
        
        # Generate new version
        new_version = f"{major}.{minor}.{patch:02d}"
        
        # Check if it matches expected
        status = "OK" if new_version == expected_version else "FAIL"
        print(f"{status} {current_version} -> {new_version} (expected: {expected_version})")
        
        if new_version != expected_version:
            print(f"  ERROR: Expected {expected_version}, got {new_version}")

if __name__ == "__main__":
    test_version_increment()
