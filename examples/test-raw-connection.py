#!/usr/bin/env python3
"""
Test raw connection to understand the authentication flow.
"""

import socket
import sys
import struct
import binascii
import hashlib

def encode_length(length):
    """Encode length for RouterOS API."""
    if length < 0x80:
        return bytes([length])
    elif length < 0x4000:
        length |= 0x8000
        return struct.pack('>H', length)
    elif length < 0x200000:
        length |= 0xC00000
        return struct.pack('>I', length)[1:]
    elif length < 0x10000000:
        length |= 0xE0000000
        return struct.pack('>I', length)
    else:
        return b'\xF0' + struct.pack('>I', length)

def encode_word(word):
    """Encode a word for RouterOS API."""
    word_bytes = word.encode('utf-8')
    return encode_length(len(word_bytes)) + word_bytes

def decode_length(sock):
    """Decode length from socket."""
    b = sock.recv(1)
    if not b:
        return None
    
    first_byte = b[0]
    
    if (first_byte & 0x80) == 0:
        return first_byte
    elif (first_byte & 0xC0) == 0x80:
        b += sock.recv(1)
        return struct.unpack('>H', b)[0] & ~0x8000
    elif (first_byte & 0xE0) == 0xC0:
        b += sock.recv(2)
        return struct.unpack('>I', b'\x00' + b)[0] & ~0xC00000
    elif (first_byte & 0xF0) == 0xE0:
        b += sock.recv(3)
        return struct.unpack('>I', b)[0] & ~0xE0000000
    elif first_byte == 0xF0:
        return struct.unpack('>I', sock.recv(4))[0]

def read_sentence(sock):
    """Read a sentence from socket."""
    words = []
    while True:
        length = decode_length(sock)
        if length is None or length == 0:
            break
        word = sock.recv(length).decode('utf-8', errors='ignore')
        words.append(word)
    return words

def send_sentence(sock, *words):
    """Send a sentence to socket."""
    for word in words:
        sock.sendall(encode_word(word))
    sock.sendall(b'\x00')  # End of sentence

def test_raw_connection(host, username, password):
    """Test raw connection with manual authentication."""
    print(f"\nTesting raw connection to {host}...")
    print("="*60)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    
    try:
        # Connect
        print(f"1. Connecting to {host}:8728...")
        sock.connect((host, 8728))
        print("✓ Socket connected\n")
        
        # Send login with username and password (plain)
        print("2. Sending login request...")
        send_sentence(sock, '/login', f'=name={username}', f'=password={password}')
        print("   Sent: /login, =name={}, =password=***".format(username))
        
        # Read response
        response = read_sentence(sock)
        print(f"   Response: {response}\n")
        
        if response and response[0] == '!done':
            # Check if we got a challenge
            ret_value = None
            for word in response:
                if word.startswith('=ret='):
                    ret_value = word[5:]
                    break
            
            if ret_value:
                print(f"3. Got challenge: {ret_value}")
                print("   This is MD5 challenge-response authentication")
                print("   Need to send hashed response...\n")
                
                # Calculate MD5 hash response
                # hash = MD5(0x00 + password + challenge)
                challenge_bytes = binascii.unhexlify(ret_value)
                hash_input = b'\x00' + password.encode('utf-8') + challenge_bytes
                hash_result = hashlib.md5(hash_input).hexdigest()
                
                print(f"4. Sending hash response: {hash_result[:20]}...")
                send_sentence(sock, '/login', f'=name={username}', f'=response=00{hash_result}')
                
                # Read final response
                final_response = read_sentence(sock)
                print(f"   Response: {final_response}\n")
                
                if final_response and final_response[0] == '!done':
                    print("✓ Authentication successful!\n")
                    
                    # Try a command
                    print("5. Testing /system/identity command...")
                    send_sentence(sock, '/system/identity/print')
                    
                    identity_response = read_sentence(sock)
                    print(f"   Response: {identity_response}\n")
                    
                    if identity_response and identity_response[0] == '!re':
                        print("✓ Command executed successfully!")
                        for word in identity_response:
                            if word.startswith('=name='):
                                print(f"   Router name: {word[6:]}")
                    else:
                        print(f"✗ Command failed: {identity_response}")
                else:
                    print(f"✗ Second login failed: {final_response}")
            else:
                print("✓ Plain authentication successful (no challenge)\n")
                
                # Try a command
                print("3. Testing /system/identity command...")
                send_sentence(sock, '/system/identity/print')
                
                identity_response = read_sentence(sock)
                print(f"   Response: {identity_response}\n")
        else:
            print(f"✗ Login failed: {response}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sock.close()
        print("\nConnection closed")
        print("="*60)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python test-raw-connection.py <IP> <USERNAME> <PASSWORD>")
        sys.exit(1)
    
    test_raw_connection(sys.argv[1], sys.argv[2], sys.argv[3])
