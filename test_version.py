import hashlib

# Simulate the get_revision function with our changes
def test_version_increment():
    # Test case 1: Patch version reaches 99
    print("Test 1: Patch version reaches 99")
    stored_revision = "1.00.99"
    major, minor, patch = map(int, stored_revision.split('.'))
    patch += 1
    
    # When patch version reaches 99, reset to 00 and increment minor version
    if patch > 99:
        patch = 0
        minor += 1
        
        # When minor version reaches 99, reset to 00 and increment major version
        if minor > 99:
            minor = 0
            major += 1
    
    new_revision = f"{major}.{minor:02d}.{patch:02d}"
    print(f"Old version: {stored_revision}")
    print(f"New version: {new_revision}")
    print(f"Expected: 1.01.00")
    print(f"Test 1 {'PASSED' if new_revision == '1.01.00' else 'FAILED'}")
    print()
    
    # Test case 2: Minor version reaches 99
    print("Test 2: Minor version reaches 99")
    stored_revision = "1.99.99"
    major, minor, patch = map(int, stored_revision.split('.'))
    patch += 1
    
    # When patch version reaches 99, reset to 00 and increment minor version
    if patch > 99:
        patch = 0
        minor += 1
        
        # When minor version reaches 99, reset to 00 and increment major version
        if minor > 99:
            minor = 0
            major += 1
    
    new_revision = f"{major}.{minor:02d}.{patch:02d}"
    print(f"Old version: {stored_revision}")
    print(f"New version: {new_revision}")
    print(f"Expected: 2.00.00")
    print(f"Test 2 {'PASSED' if new_revision == '2.00.00' else 'FAILED'}")
    print()
    
    # Test case 3: Normal increment
    print("Test 3: Normal increment")
    stored_revision = "1.01.50"
    major, minor, patch = map(int, stored_revision.split('.'))
    patch += 1
    
    # When patch version reaches 99, reset to 00 and increment minor version
    if patch > 99:
        patch = 0
        minor += 1
        
        # When minor version reaches 99, reset to 00 and increment major version
        if minor > 99:
            minor = 0
            major += 1
    
    new_revision = f"{major}.{minor:02d}.{patch:02d}"
    print(f"Old version: {stored_revision}")
    print(f"New version: {new_revision}")
    print(f"Expected: 1.01.51")
    print(f"Test 3 {'PASSED' if new_revision == '1.01.51' else 'FAILED'}")

if __name__ == "__main__":
    test_version_increment()
