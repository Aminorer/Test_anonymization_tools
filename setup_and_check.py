#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour corriger définitivement l'erreur dans anonymizer.py
"""

import os
import shutil

def fix_anonymizer_final():
    """Correction finale du fichier anonymizer.py"""
    
    file_path = "src/anonymizer.py"
    
    # Créer une sauvegarde si elle n'existe pas
    backup_path = "src/anonymizer.py.backup"
    if not os.path.exists(backup_path):
        shutil.copy(file_path, backup_path)
        print(f"Sauvegarde créée: {backup_path}")
    
    try:
        # Lire le fichier
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Fichier lu: {len(content)} caractères")
        
        # Rechercher et corriger le problème
        problematic_line = "def *entities*overlap(self, entity1: Entity, entity2: Entity) -> bool:"
        
        if problematic_line in content:
            # Remplacer par la fonction correcte
            correct_function = """def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool:
        \"\"\"Vérification de chevauchement\"\"\"
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)"""
            
            content = content.replace(problematic_line, correct_function)
            print("✅ Fonction problématique corrigée")
        else:
            print("⚠️ Fonction problématique non trouvée, recherche d'autres problèmes...")
            
            # Rechercher d'autres variantes du problème
            variations = [
                "def *entities*overlap(",
                "def entities*overlap(",
                "def *entities overlap("
            ]
            
            for variation in variations:
                if variation in content:
                    # Remplacer par la fonction correcte
                    # Trouver la fin de la ligne
                    start_pos = content.find(variation)
                    end_pos = content.find('\n', start_pos)
                    if end_pos == -1:
                        end_pos = len(content)
                    
                    old_line = content[start_pos:end_pos]
                    new_function = """def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool:
        \"\"\"Vérification de chevauchement\"\"\"
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)"""
                    
                    content = content.replace(old_line, new_function)
                    print(f"✅ Corrigé variation: {variation}")
                    break
        
        # Vérifier et corriger d'autres problèmes de syntaxe potentiels
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Détecter les définitions de fonctions sans contenu
            if line.strip().startswith('def ') and line.strip().endswith(':'):
                # Vérifier la ligne suivante
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Si la ligne suivante n'est pas indentée ou est vide
                    if next_line.strip() == '' or (next_line.strip() and not next_line.startswith('    ')):
                        # Ajouter une ligne avec pass
                        fixed_lines.append(line)
                        fixed_lines.append('    pass')
                        print(f"✅ Ajouté 'pass' après la ligne {line_num}")
                        continue
            
            fixed_lines.append(line)
        
        # Reconstruction du contenu
        content = '\n'.join(fixed_lines)
        
        # Nettoyer les éventuelles lignes vides en trop à la fin
        content = content.rstrip() + '\n'
        
        # Sauvegarder le fichier corrigé
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Fichier corrigé et sauvegardé")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la correction: {e}")
        return False

def verify_syntax():
    """Vérifier la syntaxe du fichier corrigé"""
    try:
        with open("src/anonymizer.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Compilation pour vérifier la syntaxe
        compile(content, "src/anonymizer.py", "exec")
        print("✅ Syntaxe correcte!")
        return True
        
    except SyntaxError as e:
        print(f"❌ Erreur de syntaxe ligne {e.lineno}: {e.msg}")
        if e.lineno:
            # Afficher le contexte autour de l'erreur
            lines = content.split('\n')
            start = max(0, e.lineno - 3)
            end = min(len(lines), e.lineno + 2)
            
            print("Contexte:")
            for i in range(start, end):
                marker = ">>> " if i + 1 == e.lineno else "    "
                print(f"{marker}{i+1:4d}: {lines[i]}")
        return False
        
    except Exception as e:
        print(f"❌ Autre erreur: {e}")
        return False

if __name__ == "__main__":
    print("=== CORRECTION FINALE D'ANONYMIZER.PY ===")
    
    if os.path.exists("src/anonymizer.py"):
        print("Correction en cours...")
        if fix_anonymizer_final():
            print("\n=== VÉRIFICATION DE LA SYNTAXE ===")
            verify_syntax()
        else:
            print("Échec de la correction")
    else:
        print("Fichier src/anonymizer.py non trouvé")
        print("Vérifiez le répertoire de travail")