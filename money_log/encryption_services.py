
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import os
from django.conf import settings


class EncryptionService:
    @staticmethod
    def derive_key(context:str) -> bytes:        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info = context.encode('utf-8')
        )

        return hkdf.derive(settings.ENCRYPTION_KEY)

    @staticmethod
    def encrypt(plaintext:str , context:str)-> bytes:
        try:
            
            if not settings.ENABLE_ENCRYPTION or plaintext is None:
                return plaintext

            key = EncryptionService.derive_key(context)
            aesgcm = AESGCM(key)
            nounce = os.urandom(12)
            chiper_text =  aesgcm.encrypt(nounce,plaintext.encode('utf-8'),None)

            return nounce+chiper_text
        
        except Exception as e:
            print("Error in Encrypt : ",e)
            raise

    
    @staticmethod
    def decrypt(ciphertext:bytes , context:str)->str:

        if not settings.ENABLE_ENCRYPTION or ciphertext is None:
            return ciphertext if isinstance(ciphertext, str) else (ciphertext.decode('utf-8', errors='ignore') if isinstance(ciphertext, bytes) else str(ciphertext))
        
        try:
            key = EncryptionService.derive_key(context)

            nonce = ciphertext[:12]
            data = ciphertext[12:]
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, data, None)
            return plaintext.decode('utf-8')
        except Exception as e:
            print("Error : ",e)
            raise

# Convience functions
def encrypt_field(value:str, context:str) -> bytes:
    return EncryptionService.encrypt(value,context)

def decrypt_field(value: bytes, context: str) -> str:
    """Decrypt a single field"""
    return EncryptionService.decrypt(value, context)