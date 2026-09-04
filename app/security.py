import base64, hashlib, hmac, os

def hash_password(password: str) -> str:
    salt=os.urandom(16)
    digest=hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return 'scrypt$16384$8$1$'+base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(digest).decode()

def verify_password(password: str, stored: str) -> tuple[bool,bool]:
    if stored.startswith('scrypt$'):
        try:
            _,n,r,p,salt_b64,digest_b64=stored.split('$')
            salt=base64.urlsafe_b64decode(salt_b64.encode())
            expected=base64.urlsafe_b64decode(digest_b64.encode())
            actual=hashlib.scrypt(password.encode(),salt=salt,n=int(n),r=int(r),p=int(p))
            return hmac.compare_digest(actual,expected), False
        except Exception:
            return False, False
    # Backward-compatible migration for the old local SHA-256 records.
    legacy=hashlib.sha256(password.encode('utf-8')).hexdigest()
    return hmac.compare_digest(legacy, stored), True
