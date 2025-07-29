"""
Moteur de remplacement intelligent pour éviter les conflits entre entités
"""

import re
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ReplacementRule:
    original: str
    replacement: str
    start_positions: List[int]
    length: int
    priority: int  # Plus c'est élevé, plus c'est prioritaire
    entity_id: str
    is_grouped: bool = False
    group_id: str = None
    
    def __hash__(self):
        """Rend la classe hashable pour les sets"""
        return hash((self.original, self.replacement, self.entity_id))
    
    def __eq__(self, other):
        """Égalité basée sur l'ID de l'entité"""
        if not isinstance(other, ReplacementRule):
            return False
        return self.entity_id == other.entity_id

class IntelligentReplacementEngine:
    """
    Moteur de remplacement qui évite les conflits entre entités
    en traitant les remplacements par ordre de priorité (plus long = plus prioritaire)
    """
    
    def __init__(self):
        self.rules: List[ReplacementRule] = []
        
    def add_replacement(self, original: str, replacement: str, entity_id: str, 
                       is_grouped: bool = False, group_id: str = None):
        """Ajoute une règle de remplacement"""
        # Ne pas ajouter de règles vides
        if not original.strip() or not replacement.strip():
            return
            
        rule = ReplacementRule(
            original=original.strip(),
            replacement=replacement.strip(),
            start_positions=[],
            length=len(original.strip()),
            priority=len(original.strip()),  # Plus long = plus prioritaire
            entity_id=entity_id,
            is_grouped=is_grouped,
            group_id=group_id
        )
        
        self.rules.append(rule)
        logger.debug(f"Règle ajoutée: '{original}' -> '{replacement}' (priorité: {rule.priority})")
    
    def find_all_positions(self, text: str):
        """Trouve toutes les positions de chaque règle dans le texte"""
        for rule in self.rules:
            rule.start_positions = []
            
            # Recherche insensible à la casse mais préserve la casse originale
            pattern = re.escape(rule.original)
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                rule.start_positions.append(match.start())
                
            logger.debug(f"'{rule.original}' trouvé à {len(rule.start_positions)} positions: {rule.start_positions}")
    
    def detect_conflicts(self) -> List[Tuple[ReplacementRule, ReplacementRule]]:
        """Détecte les conflits entre règles (chevauchements)"""
        conflicts = []
        
        for i, rule1 in enumerate(self.rules):
            for j, rule2 in enumerate(self.rules):
                if i >= j:
                    continue
                    
                # Vérifier si rule1 est contenue dans rule2 ou vice versa
                if (rule1.original.lower() in rule2.original.lower() or 
                    rule2.original.lower() in rule1.original.lower()):
                    conflicts.append((rule1, rule2))
                    logger.warning(f"Conflit détecté: '{rule1.original}' <-> '{rule2.original}'")
        
        return conflicts
    
    def resolve_conflicts(self, conflicts: List[Tuple[ReplacementRule, ReplacementRule]]):
        """Résout les conflits en donnant priorité aux règles les plus longues"""
        rules_to_remove_ids = set()  # Utiliser les IDs au lieu des objets
        
        for rule1, rule2 in conflicts:
            # La règle la plus longue gagne
            if rule1.priority > rule2.priority:
                rules_to_remove_ids.add(rule2.entity_id)
                logger.info(f"Conflit résolu: '{rule1.original}' prioritaire sur '{rule2.original}'")
            elif rule2.priority > rule1.priority:
                rules_to_remove_ids.add(rule1.entity_id)
                logger.info(f"Conflit résolu: '{rule2.original}' prioritaire sur '{rule1.original}'")
            else:
                # Même longueur : prioriser les groupes
                if rule1.is_grouped and not rule2.is_grouped:
                    rules_to_remove_ids.add(rule2.entity_id)
                elif rule2.is_grouped and not rule1.is_grouped:
                    rules_to_remove_ids.add(rule1.entity_id)
                else:
                    # Garder le premier par défaut
                    rules_to_remove_ids.add(rule2.entity_id)
        
        # Supprimer les règles non prioritaires
        self.rules = [rule for rule in self.rules if rule.entity_id not in rules_to_remove_ids]
        logger.info(f"Après résolution des conflits: {len(self.rules)} règles actives")
    
    def apply_replacements(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Applique tous les remplacements de manière intelligente
        Retourne le texte modifié et un rapport des remplacements effectués
        """
        if not self.rules:
            return text, {}
        
        # 1. Trouver toutes les positions
        self.find_all_positions(text)
        
        # 2. Détecter et résoudre les conflits
        conflicts = self.detect_conflicts()
        if conflicts:
            self.resolve_conflicts(conflicts)
            # Recalculer les positions après résolution
            self.find_all_positions(text)
        
        # 3. Trier les règles par priorité (plus long d'abord)
        active_rules = sorted(
            [rule for rule in self.rules if rule.start_positions],
            key=lambda r: r.priority,
            reverse=True
        )
        
        # 4. Créer la liste de tous les remplacements avec leurs positions
        all_replacements = []
        for rule in active_rules:
            for pos in rule.start_positions:
                all_replacements.append({
                    'start': pos,
                    'end': pos + rule.length,
                    'original': rule.original,
                    'replacement': rule.replacement,
                    'rule_id': rule.entity_id  # Utiliser l'ID au lieu de l'objet
                })
        
        # 5. Trier par position (de la fin vers le début pour éviter le décalage des indices)
        all_replacements.sort(key=lambda x: x['start'], reverse=True)
        
        # 6. Éliminer les chevauchements (le plus prioritaire gagne)
        final_replacements = []
        used_positions = set()
        
        for repl in all_replacements:
            # Vérifier si cette position chevauche avec une position déjà utilisée
            overlap = False
            for pos in range(repl['start'], repl['end']):
                if pos in used_positions:
                    overlap = True
                    break
            
            if not overlap:
                final_replacements.append(repl)
                # Marquer toutes les positions comme utilisées
                for pos in range(repl['start'], repl['end']):
                    used_positions.add(pos)
        
        # 7. Appliquer les remplacements (de la fin vers le début)
        final_replacements.sort(key=lambda x: x['start'], reverse=True)
        modified_text = text
        replacement_stats = {}
        
        for repl in final_replacements:
            old_text = modified_text[repl['start']:repl['end']]
            modified_text = (
                modified_text[:repl['start']] + 
                repl['replacement'] + 
                modified_text[repl['end']:]
            )
            
            # Statistiques
            original_key = repl['original']
            replacement_stats[original_key] = replacement_stats.get(original_key, 0) + 1
            
            logger.debug(f"Remplacé: '{old_text}' -> '{repl['replacement']}' à la position {repl['start']}")
        
        logger.info(f"Remplacements effectués: {sum(replacement_stats.values())} au total")
        return modified_text, replacement_stats
    
    def get_replacement_report(self) -> Dict[str, any]:
        """Génère un rapport détaillé des remplacements"""
        return {
            'total_rules': len(self.rules),
            'active_rules': len([r for r in self.rules if r.start_positions]),
            'grouped_rules': len([r for r in self.rules if r.is_grouped]),
            'rules_detail': [
                {
                    'original': rule.original,
                    'replacement': rule.replacement,
                    'occurrences': len(rule.start_positions),
                    'priority': rule.priority,
                    'is_grouped': rule.is_grouped,
                    'group_id': rule.group_id
                }
                for rule in self.rules
            ]
        }