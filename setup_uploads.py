#!/usr/bin/env python3
"""
Script para configurar la estructura de carpetas de uploads en Render
"""

import os
import sys

def setup_upload_folders():
    """Crear estructura de carpetas para uploads"""
    folders = [
        'uploads',
        'uploads/images',
        'uploads/images/temp',
        'uploads/temp'
    ]
    
    for folder in folders:
        try:
            os.makedirs(folder, exist_ok=True)
            print(f"✅ Carpeta creada: {folder}")
            
            # Crear archivo .gitkeep para mantener las carpetas en git
            gitkeep_path = os.path.join(folder, '.gitkeep')
            if not os.path.exists(gitkeep_path):
                with open(gitkeep_path, 'w') as f:
                    f.write('')
                print(f"📄 Archivo .gitkeep creado en: {folder}")
                
        except Exception as e:
            print(f"❌ Error creando carpeta {folder}: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🔧 Configurando estructura de carpetas de uploads...")
    
    if setup_upload_folders():
        print("✅ Estructura de carpetas configurada correctamente")
        sys.exit(0)
    else:
        print("❌ Error configurando carpetas")
        sys.exit(1)