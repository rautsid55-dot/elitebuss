import smtplib
import socket

print("\n--- Testing Connections to Gmail ---")

# Test Port 465 (SSL)
try:
    print("Testing Port 465 (SSL)...")
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=5)
    print("✅ Port 465 SUCCESS! Your network allows this.")
    server.quit()
except Exception as e:
    print(f"❌ Port 465 FAILED: {e}")

# Test Port 587 (TLS)
try:
    print("\nTesting Port 587 (TLS)...")
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=5)
    print("✅ Port 587 SUCCESS! Your network allows this.")
    server.quit()
except Exception as e:
    print(f"❌ Port 587 FAILED: {e}")

print("\n------------------------------------\n")