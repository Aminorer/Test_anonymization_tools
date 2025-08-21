#!/usr/bin/env python3
"""
Correction rapide des erreurs de syntaxe dans anonymizer.py
"""

def fix_anonymizer():
    """Corriger rapidement les erreurs"""
    
    print("🔧 Correction des erreurs de syntaxe...")
    
    # Lire le fichier
    with open("src/anonymizer.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Sauvegarder l'original
    with open("src/anonymizer.py.backup", "w", encoding="utf-8") as f:
        f.write(content)
    print("📋 Sauvegarde créée: src/anonymizer.py.backup")
    
    # Corrections
    fixes = 0
    
    # Correction principale
    if "re.sub(r'[.,;:!?]+, ''" in content:
        content = content.replace("re.sub(r'[.,;:!?]+, ''", "re.sub(r'[.,;:!?]+$', ''")
        fixes += 1
        print("✅ Correction 1: Expression régulière corrigée")
    
    # Autres corrections possibles
    replacements = [
        ("r'[.,;:!?]+, ''", "r'[.,;:!?]+$', ''"),
        ('r"[.,;:!?]+, ""', 'r"[.,;:!?]+$", ""'),
        ("cleaned = re.sub(r'[.,;:!?]+, '', cleaned)", "cleaned = re.sub(r'[.,;:!?]+$', '', cleaned)"),
    ]
    
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            fixes += 1
            print(f"✅ Correction: {old} → {new}")
    
    # Écrire le fichier corrigé
    with open("src/anonymizer.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"🎉 {fixes} correction(s) appliquée(s)")
    
    # Tester la syntaxe
    try:
        import ast
        ast.parse(content)
        print("✅ Syntaxe vérifiée - Fichier correct!")
        return True
    except SyntaxError as e:
        print(f"❌ Erreur persistante ligne {e.lineno}: {e.msg}")
        return False

if __name__ == "__main__":
    if fix_anonymizer():
        print("\n🚀 SUCCÈS! Vous pouvez maintenant lancer:")
        print("   streamlit run main.py")
    else:
        print("\n⚠️ Correction manuelle nécessaire")