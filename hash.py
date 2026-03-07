
import hashlib
def hash_sha256(text):
    encoded_text = text.encode('utf-8')
    
    hash = hashlib.sha256(encoded_text)

    return hash.hexdigest()


