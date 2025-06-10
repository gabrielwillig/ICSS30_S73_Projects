import string
import random

def generate_random_text_file(path, size=1024):
    """Gera um arquivo em disk com 'size' bytes aleatórios (letras e dígitos)."""
    chars = string.ascii_letters + string.digits + ' '
    with open(path, 'w') as f:
        f.write(''.join(random.choice(chars) for _ in range(size)))

