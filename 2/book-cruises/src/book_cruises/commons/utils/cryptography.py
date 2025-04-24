import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

from .logging import logger

class Cryptographer:
    def load_private_key(self, private_key_path: str) -> rsa.RSAPrivateKey:
        with open(private_key_path, "rb") as private_file:
            private_key = serialization.load_pem_private_key(
                private_file.read(),
                password=None,  # Add a password if the key is encrypted
            )
        logger.debug(f"Private key loaded from {private_key_path}")
        return private_key


    def load_public_key(self, public_key_path: str) -> rsa.RSAPublicKey:
        with open(public_key_path, "rb") as public_file:
            public_key = serialization.load_pem_public_key(public_file.read())
        logger.debug(f"Public key loaded from {public_key_path}")
        return public_key


    def sign_message(self, message: dict, private_key: rsa.RSAPrivateKey) -> str:
        """Sign the message using the private key."""
        message_bytes = json.dumps(message).encode()
        signature = private_key.sign(
            message_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        logger.debug("Message signed successfully")
        return signature.hex()

    def verify_signature(self, message: dict, signature: str, public_key: rsa.RSAPublicKey) -> bool:
        """Verify the signature using the public key."""
        message_bytes = json.dumps(message).encode()
        signature_bytes = bytes.fromhex(signature)
        try:
            public_key.verify(
                signature_bytes,
                message_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            logger.debug("Signature verified successfully")
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

cryptographer = Cryptographer()