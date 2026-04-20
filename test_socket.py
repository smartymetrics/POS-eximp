import socket
import ssl

host = "scsdnstqtrqjsosbmxyf.supabase.co"
port = 443

print(f"Connecting to {host}:{port}...")
try:
    # DNS lookup
    addr = socket.gethostbyname(host)
    print(f"DNS Resolved: {addr}")
    
    # TCP connection
    s = socket.create_connection((host, port), timeout=5)
    print("TCP connection successful")
    
    # SSL/TLS
    context = ssl.create_default_context()
    with context.wrap_socket(s, server_hostname=host) as ss:
        print("SSL handshake successful")
        print(f"Protocol: {ss.version()}")
        
    s.close()
except Exception as e:
    print(f"Connection failed: {e}")
