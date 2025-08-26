import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

class EntityManager:
    """Gestionnaire pour les entités et groupes d'entités"""
    
    def __init__(self):
        self.entities = []
        self.groups = []
        self.history = []
        self.max_history = 50
        # Cache for grouped entities to avoid recomputation
        self._grouped_entities_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def _invalidate_grouped_entities_cache(self) -> None:
        """Invalidate cached grouped entities."""
        self._grouped_entities_cache = None
    
    def add_entity(self, entity_data: Dict[str, Any]) -> str:
        """Ajouter une nouvelle entité"""
        try:
            # Générer un ID unique si pas fourni
            if 'id' not in entity_data:
                entity_data['id'] = str(uuid.uuid4())
            
            # Ajouter timestamp
            entity_data['created_at'] = datetime.now().isoformat()
            entity_data['updated_at'] = entity_data['created_at']
            
            # Valider les champs requis
            required_fields = ['type', 'value', 'start', 'end']
            for field in required_fields:
                if field not in entity_data:
                    raise ValueError(f"Champ requis manquant: {field}")
            
            # Ajouter à la liste
            self.entities.append(entity_data)
            # Cache des groupes obsolète
            self._invalidate_grouped_entities_cache()
            
            # Sauvegarder dans l'historique
            self._save_to_history("add_entity", entity_data['id'])
            
            logging.info(f"Entity added: {entity_data['id']}")
            return entity_data['id']
            
        except ValueError as e:
            # Missing required fields are reported as ValueError
            logging.error(f"Error adding entity: {str(e)}")
            raise
    
    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> bool:
        """Mettre à jour une entité existante"""
        try:
            entity = self.get_entity_by_id(entity_id)
            if not entity:
                logging.warning(f"Entity not found: {entity_id}")
                return False
            
            # Sauvegarder l'état précédent
            old_entity = entity.copy()
            
            # Appliquer les mises à jour
            entity.update(updates)
            entity['updated_at'] = datetime.now().isoformat()
            # Invalidate grouped cache as entity data changed
            self._invalidate_grouped_entities_cache()
            
            # Sauvegarder dans l'historique
            self._save_to_history("update_entity", entity_id, old_entity)
            
            logging.info(f"Entity updated: {entity_id}")
            return True
            
        except (KeyError, TypeError) as e:
            # Updating with invalid keys or data types is handled gracefully
            logging.error(f"Error updating entity: {str(e)}")
            return False
    
    def delete_entity(self, entity_id: str) -> bool:
        """Supprimer une entité"""
        try:
            entity = self.get_entity_by_id(entity_id)
            if not entity:
                logging.warning(f"Entity not found: {entity_id}")
                return False
            
            # Sauvegarder pour l'historique
            deleted_entity = entity.copy()
            
            # Supprimer de la liste
            self.entities = [e for e in self.entities if e['id'] != entity_id]
            # Invalidate grouped cache as entities changed
            self._invalidate_grouped_entities_cache()
            
            # Supprimer des groupes
            self._remove_entity_from_all_groups(entity_id)
            
            # Sauvegarder dans l'historique
            self._save_to_history("delete_entity", entity_id, deleted_entity)
            
            logging.info(f"Entity deleted: {entity_id}")
            return True
            
        except (KeyError, ValueError) as e:
            # Issues manipulating entity lists are treated as deletion failures
            logging.error(f"Error deleting entity: {str(e)}")
            return False

    def update_token_variants(self, token: str, variant: str) -> None:
        """Mettre à jour toutes les entités partageant un même jeton."""
        updated = False
        for entity in self.entities:
            if entity.get("replacement") == token:
                variants = set(entity.get("variants", []))
                if variant not in variants:
                    variants.add(variant)
                    entity["variants"] = list(variants)
                    entity["updated_at"] = datetime.now().isoformat()
                    updated = True
        if updated:
            # Invalidate cache only if something changed
            self._invalidate_grouped_entities_cache()

    def get_grouped_entities(self) -> Dict[str, Dict[str, Any]]:
        """Group entities by their replacement token and provide statistics.

        Returns:
            A dictionary keyed by group id (e.g. "PERSON_1") containing:
            - type: entity type
            - token: replacement token
            - total_occurrences: total entities using this token
            - variants: mapping of original values to their stats
                Each variant stores: value, count, positions
        """
        if self._grouped_entities_cache is not None:
            return self._grouped_entities_cache

        grouped: Dict[str, Dict[str, Any]] = {}
        for entity in self.entities:
            token = entity.get("replacement")
            if not token:
                continue
            group_id = token.strip("[]")
            group = grouped.setdefault(
                group_id,
                {
                    "id": group_id,
                    "type": entity.get("type"),
                    "token": token,
                    "total_occurrences": 0,
                    "variants": {},
                },
            )

            group["total_occurrences"] += 1

            value = entity.get("value")
            variant_entry = group["variants"].setdefault(
                value,
                {"value": value, "count": 0, "positions": []},
            )
            variant_entry["count"] += 1
            variant_entry["positions"].append(
                {"start": entity.get("start"), "end": entity.get("end")}
            )

        self._grouped_entities_cache = grouped
        return grouped
    
    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer une entité par son ID"""
        for entity in self.entities:
            if entity['id'] == entity_id:
                return entity
        return None
    
    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """Récupérer toutes les entités d'un type donné"""
        return [entity for entity in self.entities if entity.get('type') == entity_type]
    
    def get_entities_by_confidence(self, min_confidence: float) -> List[Dict[str, Any]]:
        """Récupérer les entités avec une confiance minimale"""
        return [
            entity for entity in self.entities 
            if entity.get('confidence', 1.0) >= min_confidence
        ]
    
    def search_entities(self, query: str, search_fields: List[str] = None) -> List[Dict[str, Any]]:
        """Rechercher des entités par texte"""
        if search_fields is None:
            search_fields = ['value', 'type', 'replacement']
        
        query = query.lower()
        results = []
        
        for entity in self.entities:
            for field in search_fields:
                if field in entity and query in str(entity[field]).lower():
                    results.append(entity)
                    break
        
        return results
    
    def filter_entities(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filtrer les entités selon des critères"""
        filtered = self.entities.copy()
        
        # Filtre par type
        if 'types' in filters and filters['types']:
            filtered = [e for e in filtered if e.get('type') in filters['types']]
        
        # Filtre par confiance
        if 'min_confidence' in filters:
            min_conf = filters['min_confidence']
            filtered = [e for e in filtered if e.get('confidence', 1.0) >= min_conf]
        
        # Filtre par texte
        if 'text' in filters and filters['text']:
            query = filters['text'].lower()
            filtered = [
                e for e in filtered 
                if query in e.get('value', '').lower() or query in e.get('type', '').lower()
            ]
        
        # Filtre par groupe
        if 'group_id' in filters and filters['group_id']:
            group = self.get_group_by_id(filters['group_id'])
            if group:
                group_entity_ids = set(group.get('entity_ids', []))
                filtered = [e for e in filtered if e['id'] in group_entity_ids]
        
        return filtered
    
    def sort_entities(self, entities: List[Dict[str, Any]], sort_by: str = 'start', 
                     reverse: bool = False) -> List[Dict[str, Any]]:
        """Trier les entités"""
        valid_sort_fields = ['start', 'end', 'type', 'value', 'confidence', 'created_at']
        
        if sort_by not in valid_sort_fields:
            sort_by = 'start'
        
        try:
            return sorted(
                entities, 
                key=lambda x: x.get(sort_by, 0) if sort_by in ['start', 'end', 'confidence'] else str(x.get(sort_by, '')),
                reverse=reverse
            )
        except TypeError as e:
            # Sorting may fail if keys contain incomparable values
            logging.error(f"Error sorting entities: {str(e)}")
            return entities
    
    # Gestion des groupes
    
    def create_group(self, name: str, description: str = "", entity_ids: List[str] = None) -> str:
        """Créer un nouveau groupe d'entités"""
        try:
            group_id = str(uuid.uuid4())
            group_data = {
                'id': group_id,
                'name': name,
                'description': description,
                'entity_ids': entity_ids or [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.groups.append(group_data)
            
            # Sauvegarder dans l'historique
            self._save_to_history("create_group", group_id)
            
            logging.info(f"Group created: {group_id}")
            return group_id
            
        except ValueError as e:
            # Invalid input for group creation should surface as ValueError
            logging.error(f"Error creating group: {str(e)}")
            raise
    
    def update_group(self, group_id: str, updates: Dict[str, Any]) -> bool:
        """Mettre à jour un groupe"""
        try:
            group = self.get_group_by_id(group_id)
            if not group:
                logging.warning(f"Group not found: {group_id}")
                return False
            
            # Sauvegarder l'état précédent
            old_group = group.copy()
            
            # Appliquer les mises à jour
            group.update(updates)
            group['updated_at'] = datetime.now().isoformat()
            
            # Sauvegarder dans l'historique
            self._save_to_history("update_group", group_id, old_group)
            
            logging.info(f"Group updated: {group_id}")
            return True
            
        except (KeyError, TypeError) as e:
            # Updating with invalid keys or structures is handled gracefully
            logging.error(f"Error updating group: {str(e)}")
            return False
    
    def delete_group(self, group_id: str) -> bool:
        """Supprimer un groupe"""
        try:
            group = self.get_group_by_id(group_id)
            if not group:
                logging.warning(f"Group not found: {group_id}")
                return False
            
            # Sauvegarder pour l'historique
            deleted_group = group.copy()
            
            # Supprimer de la liste
            self.groups = [g for g in self.groups if g['id'] != group_id]
            
            # Sauvegarder dans l'historique
            self._save_to_history("delete_group", group_id, deleted_group)
            
            logging.info(f"Group deleted: {group_id}")
            return True
            
        except (KeyError, ValueError) as e:
            # Errors removing group data are logged but not raised
            logging.error(f"Error deleting group: {str(e)}")
            return False

    def delete_group_by_token(self, token_id: str) -> int:
        """Delete all entities associated with a replacement token.

        Args:
            token_id: Identifier of the token without surrounding brackets.

        Returns:
            The number of entities deleted.
        """

        token = f"[{token_id}]"
        to_delete = [e for e in self.entities if e.get("replacement") == token]
        if not to_delete:
            logging.warning(f"No entities found for token: {token_id}")
            return 0

        for entity in to_delete:
            self._save_to_history("delete_entity", entity["id"], entity.copy())
            self._remove_entity_from_all_groups(entity["id"])
            logging.info(f"Entity deleted: {entity['id']}")

        # Remove entities from list
        self.entities = [e for e in self.entities if e.get("replacement") != token]

        # Invalidate grouped cache since entities changed
        self._invalidate_grouped_entities_cache()

        logging.info(f"Group deleted by token: {token_id}")
        return len(to_delete)
    
    def get_group_by_id(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer un groupe par son ID"""
        for group in self.groups:
            if group['id'] == group_id:
                return group
        return None
    
    def add_entity_to_group(self, group_id: str, entity_id: str) -> bool:
        """Ajouter une entité à un groupe"""
        try:
            group = self.get_group_by_id(group_id)
            entity = self.get_entity_by_id(entity_id)
            
            if not group or not entity:
                logging.warning(f"Group or entity not found: {group_id}, {entity_id}")
                return False
            
            if entity_id not in group['entity_ids']:
                group['entity_ids'].append(entity_id)
                group['updated_at'] = datetime.now().isoformat()
                
                # Sauvegarder dans l'historique
                self._save_to_history("add_entity_to_group", f"{group_id}:{entity_id}")
                
                logging.info(f"Entity {entity_id} added to group {group_id}")
                return True
            
            return True  # Déjà dans le groupe
            
        except KeyError as e:
            # Missing expected keys when modifying groups is handled gracefully
            logging.error(f"Error adding entity to group: {str(e)}")
            return False
    
    def remove_entity_from_group(self, group_id: str, entity_id: str) -> bool:
        """Retirer une entité d'un groupe"""
        try:
            group = self.get_group_by_id(group_id)
            if not group:
                logging.warning(f"Group not found: {group_id}")
                return False
            
            if entity_id in group['entity_ids']:
                group['entity_ids'].remove(entity_id)
                group['updated_at'] = datetime.now().isoformat()
                
                # Sauvegarder dans l'historique
                self._save_to_history("remove_entity_from_group", f"{group_id}:{entity_id}")
                
                logging.info(f"Entity {entity_id} removed from group {group_id}")
                return True
            
            return True  # Pas dans le groupe
            
        except KeyError as e:
            # Missing keys while removing entities from groups
            logging.error(f"Error removing entity from group: {str(e)}")
            return False
    
    def get_entities_in_group(self, group_id: str) -> List[Dict[str, Any]]:
        """Récupérer toutes les entités d'un groupe"""
        group = self.get_group_by_id(group_id)
        if not group:
            return []
        
        return [
            entity for entity in self.entities 
            if entity['id'] in group['entity_ids']
        ]
    
    def _remove_entity_from_all_groups(self, entity_id: str):
        """Retirer une entité de tous les groupes"""
        for group in self.groups:
            if entity_id in group['entity_ids']:
                group['entity_ids'].remove(entity_id)
                group['updated_at'] = datetime.now().isoformat()
    
    # Historique et undo/redo
    
    def _save_to_history(self, action: str, target_id: str, old_data: Dict = None):
        """Sauvegarder une action dans l'historique"""
        history_entry = {
            'id': str(uuid.uuid4()),
            'action': action,
            'target_id': target_id,
            'old_data': old_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.history.append(history_entry)
        
        # Limiter la taille de l'historique
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def undo_last_action(self) -> bool:
        """Annuler la dernière action"""
        if not self.history:
            return False
        
        try:
            last_action = self.history.pop()
            action = last_action['action']
            target_id = last_action['target_id']
            old_data = last_action['old_data']
            
            if action == "add_entity":
                # Annuler l'ajout = supprimer
                self.entities = [e for e in self.entities if e['id'] != target_id]
                
            elif action == "delete_entity":
                # Annuler la suppression = réajouter
                if old_data:
                    self.entities.append(old_data)
                    
            elif action == "update_entity":
                # Annuler la modification = restaurer l'ancien état
                if old_data:
                    entity = self.get_entity_by_id(target_id)
                    if entity:
                        entity.clear()
                        entity.update(old_data)
                        
            elif action == "create_group":
                # Annuler la création = supprimer
                self.groups = [g for g in self.groups if g['id'] != target_id]
                
            elif action == "delete_group":
                # Annuler la suppression = réajouter
                if old_data:
                    self.groups.append(old_data)
                    
            elif action == "update_group":
                # Annuler la modification = restaurer l'ancien état
                if old_data:
                    group = self.get_group_by_id(target_id)
                    if group:
                        group.clear()
                        group.update(old_data)
                        
            elif action in ["add_entity_to_group", "remove_entity_from_group"]:
                # Gérer les actions de groupe
                group_id, entity_id = target_id.split(':')
                if action == "add_entity_to_group":
                    self.remove_entity_from_group(group_id, entity_id)
                else:
                    self.add_entity_to_group(group_id, entity_id)
            
            logging.info(f"Action undone: {action}")
            return True
            
        except (ValueError, KeyError) as e:
            # Undo may fail if history entries are malformed
            logging.error(f"Error undoing action: {str(e)}")
            return False
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupérer l'historique des actions"""
        return self.history[-limit:] if limit > 0 else self.history
    
    def clear_history(self):
        """Vider l'historique"""
        self.history.clear()
        logging.info("History cleared")
    
    # Import/Export
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Exporter toutes les données vers un dictionnaire"""
        return {
            'entities': self.entities,
            'groups': self.groups,
            'exported_at': datetime.now().isoformat(),
            'version': '1.0'
        }
    
    def import_from_dict(self, data: Dict[str, Any], merge: bool = False):
        """Importer des données depuis un dictionnaire"""
        try:
            if not merge:
                self.entities.clear()
                self.groups.clear()
                self.clear_history()
            
            # Importer les entités
            if 'entities' in data:
                for entity_data in data['entities']:
                    if merge:
                        # Vérifier si l'entité existe déjà
                        existing = self.get_entity_by_id(entity_data['id'])
                        if existing:
                            existing.update(entity_data)
                        else:
                            self.entities.append(entity_data)
                    else:
                        self.entities.append(entity_data)
            
            # Importer les groupes
            if 'groups' in data:
                for group_data in data['groups']:
                    if merge:
                        # Vérifier si le groupe existe déjà
                        existing = self.get_group_by_id(group_data['id'])
                        if existing:
                            existing.update(group_data)
                        else:
                            self.groups.append(group_data)
                    else:
                        self.groups.append(group_data)
            
            logging.info(f"Data imported: {len(self.entities)} entities, {len(self.groups)} groups")
            
        except (KeyError, TypeError, ValueError) as e:
            # Input data not matching expected structure triggers these errors
            logging.error(f"Error importing data: {str(e)}")
            raise
    
    def export_to_json(self, file_path: str) -> bool:
        """Exporter vers un fichier JSON"""
        try:
            data = self.export_to_dict()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            logging.info(f"Data exported to {file_path}")
            return True
            
        except (OSError, TypeError) as e:
            # File writing or serialization issues during export
            logging.error(f"Error exporting to JSON: {str(e)}")
            return False
    
    def import_from_json(self, file_path: str, merge: bool = False) -> bool:
        """Importer depuis un fichier JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.import_from_dict(data, merge)
            logging.info(f"Data imported from {file_path}")
            return True
            
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            # Handle file access, JSON parsing, or data-structure issues
            logging.error(f"Error importing from JSON: {str(e)}")
            return False
    
    # Statistiques et analyse
    
    def get_statistics(self, thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Récupérer des statistiques sur les entités et groupes"""
        entity_types = {}
        confidence_values = []
        
        for entity in self.entities:
            entity_type = entity.get('type', 'UNKNOWN')
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            if 'confidence' in entity:
                confidence_values.append(entity['confidence'])
        
        # Statistiques de confiance
        confidence_stats = {}
        thresholds = thresholds or {"high": 0.8, "medium": 0.5}
        if confidence_values:
            high = thresholds.get("high", 0.8)
            medium = thresholds.get("medium", 0.5)
            confidence_stats = {
                'min': min(confidence_values),
                'max': max(confidence_values),
                'average': sum(confidence_values) / len(confidence_values),
                'high_confidence_count': len([c for c in confidence_values if c >= high]),
                'medium_confidence_count': len([c for c in confidence_values if medium <= c < high]),
                'low_confidence_count': len([c for c in confidence_values if c < medium])
            }
        
        # Statistiques des groupes
        group_sizes = [len(group.get('entity_ids', [])) for group in self.groups]
        group_stats = {}
        if group_sizes:
            group_stats = {
                'total_groups': len(self.groups),
                'average_size': sum(group_sizes) / len(group_sizes),
                'largest_group': max(group_sizes),
                'smallest_group': min(group_sizes),
                'empty_groups': len([size for size in group_sizes if size == 0])
            }
        
        return {
            'total_entities': len(self.entities),
            'total_groups': len(self.groups),
            'entity_types': entity_types,
            'confidence_stats': confidence_stats,
            'group_stats': group_stats,
            'most_common_type': max(entity_types, key=entity_types.get) if entity_types else None,
            'history_size': len(self.history)
        }
    
    def validate_data_integrity(self) -> List[str]:
        """Valider l'intégrité des données"""
        issues = []
        
        # Vérifier les entités
        entity_ids = set()
        for i, entity in enumerate(self.entities):
            # IDs uniques
            if entity['id'] in entity_ids:
                issues.append(f"Entité dupliquée: {entity['id']}")
            entity_ids.add(entity['id'])
            
            # Champs requis
            required_fields = ['id', 'type', 'value', 'start', 'end']
            for field in required_fields:
                if field not in entity:
                    issues.append(f"Entité {i}: champ manquant '{field}'")
            
            # Cohérence des positions
            if ('start' in entity and 'end' in entity and 
                entity['start'] >= entity['end']):
                issues.append(f"Entité {entity['id']}: position incohérente")
        
        # Vérifier les groupes
        group_ids = set()
        for i, group in enumerate(self.groups):
            # IDs uniques
            if group['id'] in group_ids:
                issues.append(f"Groupe dupliqué: {group['id']}")
            group_ids.add(group['id'])
            
            # Champs requis
            if 'name' not in group:
                issues.append(f"Groupe {i}: nom manquant")
            
            # Entités référencées
            for entity_id in group.get('entity_ids', []):
                if entity_id not in entity_ids:
                    issues.append(f"Groupe {group['id']}: entité inexistante '{entity_id}'")
        
        return issues
    
    def cleanup_orphaned_references(self) -> int:
        """Nettoyer les références orphelines"""
        cleaned = 0
        valid_entity_ids = set(entity['id'] for entity in self.entities)
        
        # Nettoyer les groupes
        for group in self.groups:
            original_size = len(group.get('entity_ids', []))
            group['entity_ids'] = [
                eid for eid in group.get('entity_ids', []) 
                if eid in valid_entity_ids
            ]
            cleaned += original_size - len(group['entity_ids'])
            
            if original_size != len(group['entity_ids']):
                group['updated_at'] = datetime.now().isoformat()
        
        if cleaned > 0:
            logging.info(f"Cleaned {cleaned} orphaned references")
        
        return cleaned
    
    def get_entity_conflicts(self) -> List[Dict[str, Any]]:
        """Détecter les conflits entre entités.

        Deux types de conflits sont identifiés:
        - ``overlap`` : lorsque deux entités se chevauchent dans le texte.
        - ``token`` : lorsqu'une même valeur est associée à plusieurs jetons de
          remplacement différents.
        """
        conflicts: List[Dict[str, Any]] = []

        # --- Conflits de chevauchement ---
        sorted_entities = sorted(self.entities, key=lambda x: x.get('start', 0))

        for i, entity1 in enumerate(sorted_entities):
            for entity2 in sorted_entities[i + 1:]:
                start1, end1 = entity1.get('start', 0), entity1.get('end', 0)
                start2, end2 = entity2.get('start', 0), entity2.get('end', 0)

                if start2 >= end1:
                    break  # Plus de chevauchement possible

                if start1 < end2 and start2 < end1:
                    conflicts.append(
                        {
                            'type': 'overlap',
                            'entity1': entity1,
                            'entity2': entity2,
                            'overlap_start': max(start1, start2),
                            'overlap_end': min(end1, end2),
                            'overlap_length': min(end1, end2) - max(start1, start2),
                        }
                    )

        # --- Conflits de jetons identiques pour des valeurs différentes ---
        value_tokens: Dict[str, set] = {}
        for entity in self.entities:
            value = entity.get('value')
            token = entity.get('replacement')
            if value and token:
                value_tokens.setdefault(value, set()).add(token)

        for value, tokens in value_tokens.items():
            if len(tokens) > 1:
                conflicts.append(
                    {
                        'type': 'token',
                        'value': value,
                        'tokens': sorted(tokens),
                    }
                )

        return conflicts
    
    def resolve_entity_conflicts(self, resolution_strategy: str = 'keep_highest_confidence') -> int:
        """Résoudre les conflits entre entités"""
        conflicts = self.get_entity_conflicts()
        resolved = 0
        
        for conflict in conflicts:
            entity1 = conflict['entity1']
            entity2 = conflict['entity2']
            
            if resolution_strategy == 'keep_highest_confidence':
                conf1 = entity1.get('confidence', 1.0)
                conf2 = entity2.get('confidence', 1.0)
                
                if conf1 > conf2:
                    self.delete_entity(entity2['id'])
                elif conf2 > conf1:
                    self.delete_entity(entity1['id'])
                else:
                    # Même confiance, garder le plus long
                    len1 = entity1.get('end', 0) - entity1.get('start', 0)
                    len2 = entity2.get('end', 0) - entity2.get('start', 0)
                    if len1 >= len2:
                        self.delete_entity(entity2['id'])
                    else:
                        self.delete_entity(entity1['id'])
                
                resolved += 1
            
            elif resolution_strategy == 'keep_longest':
                len1 = entity1.get('end', 0) - entity1.get('start', 0)
                len2 = entity2.get('end', 0) - entity2.get('start', 0)
                
                if len1 >= len2:
                    self.delete_entity(entity2['id'])
                else:
                    self.delete_entity(entity1['id'])
                
                resolved += 1
        
        if resolved > 0:
            logging.info(f"Resolved {resolved} entity conflicts")

        return resolved

    # --- Helpers de résolution de conflits ---

    def split_entity(self, entity_id: str, splits: List[Dict[str, Any]]) -> List[str]:
        """Diviser une entité en plusieurs segments.

        Args:
            entity_id: identifiant de l'entité à diviser.
            splits: liste de dictionnaires ``{"start": int, "end": int, "value": str}``
                décrivant les nouveaux segments.

        Returns:
            Liste des identifiants des nouvelles entités créées.
        """
        original = self.get_entity_by_id(entity_id)
        if not original:
            return []

        # Retirer l'entité originale
        self.delete_entity(entity_id)

        new_ids: List[str] = []
        for data in splits:
            new_entity = original.copy()
            new_entity.pop('id', None)
            new_entity.update({
                'start': data.get('start'),
                'end': data.get('end'),
                'value': data.get('value', original.get('value')),
            })
            # Utiliser add_entity pour garantir la cohérence
            new_ids.append(self.add_entity(new_entity))

        # Remplacer les références dans les groupes
        for group in self.groups:
            if entity_id in group.get('entity_ids', []):
                group['entity_ids'].remove(entity_id)
                group['entity_ids'].extend(new_ids)
                group['updated_at'] = datetime.now().isoformat()

        self._invalidate_grouped_entities_cache()
        return new_ids

    def merge_entity_groups(self, source_token: str, target_token: str) -> int:
        """Fusionner deux groupes basés sur le jeton de remplacement.

        Toutes les entités utilisant ``source_token`` seront réassignées vers
        ``target_token``.

        Returns:
            Le nombre d'entités modifiées.
        """
        modified = 0
        for entity in self.entities:
            if entity.get('replacement') == source_token:
                entity['replacement'] = target_token
                entity['updated_at'] = datetime.now().isoformat()
                modified += 1

        if modified:
            self._invalidate_grouped_entities_cache()

        return modified

    def reassign_variant(self, value: str, from_token: str, to_token: str) -> int:
        """Réassigner une variante d'un groupe à un autre.

        Args:
            value: valeur de la variante à déplacer.
            from_token: jeton d'origine.
            to_token: nouveau jeton.

        Returns:
            Nombre d'entités mises à jour.
        """
        moved = 0
        for entity in self.entities:
            if (
                entity.get('value') == value
                and entity.get('replacement') == from_token
            ):
                entity['replacement'] = to_token
                entity['updated_at'] = datetime.now().isoformat()
                moved += 1

        if moved:
            self._invalidate_grouped_entities_cache()

        return moved
    
    def auto_group_entities(self, strategy: str = 'by_type') -> int:
        """Grouper automatiquement les entités"""
        groups_created = 0
        
        if strategy == 'by_type':
            entity_types = {}
            for entity in self.entities:
                entity_type = entity.get('type', 'UNKNOWN')
                if entity_type not in entity_types:
                    entity_types[entity_type] = []
                entity_types[entity_type].append(entity['id'])
            
            for entity_type, entity_ids in entity_types.items():
                if len(entity_ids) > 1:  # Créer un groupe seulement s'il y a plusieurs entités
                    group_name = f"Groupe {entity_type}"
                    group_description = f"Entités de type {entity_type} groupées automatiquement"
                    
                    # Vérifier si un groupe avec ce nom existe déjà
                    existing_group = None
                    for group in self.groups:
                        if group['name'] == group_name:
                            existing_group = group
                            break
                    
                    if existing_group:
                        # Ajouter les entités au groupe existant
                        for entity_id in entity_ids:
                            self.add_entity_to_group(existing_group['id'], entity_id)
                    else:
                        # Créer un nouveau groupe
                        group_id = self.create_group(group_name, group_description, entity_ids)
                        groups_created += 1
        
        if groups_created > 0:
            logging.info(f"Auto-created {groups_created} groups")
        
        return groups_created
