#!/usr/bin/env python3
import sys
import os

sys.path.append('/app/backend')

def main():
    from app.tasks import classificar_imagem_batch
    result = classificar_imagem_batch()
    print(f"Resultado: {result}")

if __name__ == "__main__":
    main()