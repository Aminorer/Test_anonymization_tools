import os
import tempfile
import uuid
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import hashlib
import json

def format_file_size(size_bytes: int) -> str:
    """Formater la taille d'un fichier en unités lisibles"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def save_upload_file(uploaded_file) -> str:
    """Sauvegarder un fichier uploadé dans un répertoire temporaire"""
    try:
        # Créer un nom de fichier unique
        file_extension = Path(uploaded_file.name).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        
        # Créer le répertoire temporaire s'il n'existe pas
        temp_dir = Path(tempfile.gettempdir()) / "anonymizer_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        # Chemin complet du fichier
        file_path = temp_dir / unique_filename
        
        # Sauvegarder le fichier
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        logging.info(f"File saved: {file_path}")
        return str(file_path)
        
    except OSError as e:
        # Filesystem operations (mkdir/open) can fail due to permission issues
        logging.error(f"Error saving uploaded file: {str(e)}")
        raise RuntimeError(f"Failed to save uploaded file: {str(e)}") from e

def cleanup_temp_files(max_age_hours: int = 24):
    """Nettoyer les fichiers temporaires anciens"""
    try:
        temp_dir = Path(tempfile.gettempdir()) / "anonymizer_uploads"
        
        if not temp_dir.exists():
            return
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        files_cleaned = 0
        
        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    try:
                        file_path.unlink()
                        files_cleaned += 1
                    except OSError as e:
                        # Deletion may fail if the file is in use or permissions are lacking
                        logging.warning(f"Could not delete {file_path}: {str(e)}")
        
        if files_cleaned > 0:
            logging.info(f"Cleaned up {files_cleaned} temporary files")
            
    except OSError as e:
        # Issues accessing the temporary directory should be reported
        logging.error(f"Error during cleanup: {str(e)}")

def generate_file_hash(file_path: str) -> str:
    """Générer un hash MD5 d'un fichier"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except OSError as e:
        # Opening/reading the file can raise OSError if the path is invalid
        logging.error(f"Error generating file hash: {str(e)}")
        return ""

def validate_file_type(file_path: str, allowed_extensions: List[str]) -> bool:
    """Valider le type de fichier"""
    file_extension = Path(file_path).suffix.lower().lstrip('.')
    return file_extension in [ext.lower() for ext in allowed_extensions]

def sanitize_filename(filename: str) -> str:
    """Nettoyer un nom de fichier pour le rendre sûr"""
    # Caractères interdits dans les noms de fichiers
    forbidden_chars = '<>:"/\\|?*'
    
    # Remplacer les caractères interdits par des underscores
    for char in forbidden_chars:
        filename = filename.replace(char, '_')
    
    # Limiter la longueur
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        available_length = max_length - len(ext)
        filename = name[:available_length] + ext
    
    return filename

def create_safe_directory(path: str) -> str:
    """Créer un répertoire de manière sécurisée"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return path
    except OSError as e:
        # Directory creation may fail (e.g., permissions)
        logging.error(f"Error creating directory {path}: {str(e)}")
        raise

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Obtenir des informations détaillées sur un fichier"""
    try:
        file_stat = Path(file_path).stat()
        return {
            "name": Path(file_path).name,
            "size": file_stat.st_size,
            "size_formatted": format_file_size(file_stat.st_size),
            "extension": Path(file_path).suffix.lower(),
            "created": datetime.fromtimestamp(file_stat.st_ctime),
            "modified": datetime.fromtimestamp(file_stat.st_mtime),
            "hash": generate_file_hash(file_path)
        }
    except OSError as e:
        # Stat or access errors mean the file information cannot be retrieved
        logging.error(f"Error getting file info: {str(e)}")
        return {}

def export_entities_to_json(entities: List[Dict], output_path: str) -> bool:
    """Exporter les entités vers un fichier JSON"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(entities, f, ensure_ascii=False, indent=2, default=str)
        logging.info(f"Entities exported to {output_path}")
        return True
    except (OSError, TypeError) as e:
        # Writing to disk or JSON serialisation errors are expected here
        logging.error(f"Error exporting entities: {str(e)}")
        return False

def import_entities_from_json(json_path: str) -> List[Dict]:
    """Importer des entités depuis un fichier JSON"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            entities = json.load(f)
        logging.info(f"Entities imported from {json_path}")
        return entities
    except (OSError, json.JSONDecodeError) as e:
        # Handle file access or JSON parsing issues during import
        logging.error(f"Error importing entities: {str(e)}")
        return []

def merge_entities(entities1: List[Dict], entities2: List[Dict]) -> List[Dict]:
    """Fusionner deux listes d'entités en évitant les doublons"""
    merged = []
    seen_entities = set()
    
    for entity_list in [entities1, entities2]:
        for entity in entity_list:
            # Créer une clé unique basée sur type, valeur et position
            entity_key = (
                entity.get('type', ''),
                entity.get('value', ''),
                entity.get('start', 0),
                entity.get('end', 0)
            )
            
            if entity_key not in seen_entities:
                merged.append(entity)
                seen_entities.add(entity_key)
    
    return merged

def filter_entities_by_confidence(entities: List[Dict], min_confidence: float) -> List[Dict]:
    """Filtrer les entités par seuil de confiance"""
    return [
        entity for entity in entities 
        if entity.get('confidence', 1.0) >= min_confidence
    ]

def filter_entities_by_type(entities: List[Dict], entity_types: List[str]) -> List[Dict]:
    """Filtrer les entités par type"""
    return [
        entity for entity in entities 
        if entity.get('type', '') in entity_types
    ]

def sort_entities_by_position(entities: List[Dict]) -> List[Dict]:
    """Trier les entités par position dans le texte"""
    return sorted(entities, key=lambda x: (x.get('start', 0), x.get('end', 0)))

def calculate_text_coverage(entities: List[Dict], text_length: int) -> float:
    """Calculer le pourcentage du texte couvert par les entités"""
    if text_length == 0:
        return 0.0
    
    total_covered = 0
    covered_ranges = []
    
    # Trier les entités par position
    sorted_entities = sort_entities_by_position(entities)
    
    for entity in sorted_entities:
        start = entity.get('start', 0)
        end = entity.get('end', 0)
        
        # Fusionner les plages qui se chevauchent
        merged = False
        for i, (range_start, range_end) in enumerate(covered_ranges):
            if start <= range_end and end >= range_start:
                # Fusion des plages
                covered_ranges[i] = (min(start, range_start), max(end, range_end))
                merged = True
                break
        
        if not merged:
            covered_ranges.append((start, end))
    
    # Calculer la couverture totale
    for start, end in covered_ranges:
        total_covered += end - start
    
    return (total_covered / text_length) * 100

def generate_anonymization_stats(entities: List[Dict], text_length: int) -> Dict[str, Any]:
    """Générer des statistiques complètes d'anonymisation"""
    if not entities:
        return {
            "total_entities": 0,
            "entity_types": {},
            "coverage_percentage": 0.0,
            "confidence_stats": {},
            "recommendations": []
        }
    
    # Statistiques de base
    total_entities = len(entities)
    entity_types = {}
    confidences = []
    
    for entity in entities:
        entity_type = entity.get('type', 'UNKNOWN')
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        if 'confidence' in entity:
            confidences.append(entity['confidence'])
    
    # Statistiques de confiance
    confidence_stats = {}
    if confidences:
        confidence_stats = {
            "min": min(confidences),
            "max": max(confidences),
            "average": sum(confidences) / len(confidences),
            "high_confidence_count": len([c for c in confidences if c >= 0.8]),
            "low_confidence_count": len([c for c in confidences if c < 0.5])
        }
    
    # Couverture du texte
    coverage = calculate_text_coverage(entities, text_length)
    
    # Recommandations
    recommendations = generate_recommendations(entities, confidence_stats, coverage)
    
    return {
        "total_entities": total_entities,
        "entity_types": entity_types,
        "coverage_percentage": coverage,
        "confidence_stats": confidence_stats,
        "recommendations": recommendations,
        "most_common_type": max(entity_types, key=entity_types.get) if entity_types else None
    }

def generate_recommendations(entities: List[Dict], confidence_stats: Dict, coverage: float) -> List[str]:
    """Générer des recommandations basées sur l'analyse"""
    recommendations = []
    
    # Recommandations basées sur la confiance
    if confidence_stats.get('low_confidence_count', 0) > 0:
        recommendations.append(
            f"⚠️ {confidence_stats['low_confidence_count']} entités ont une confiance faible (<50%). "
            "Vérifiez-les manuellement."
        )
    
    # Recommandations basées sur la couverture
    if coverage > 50:
        recommendations.append(
            f"📊 {coverage:.1f}% du texte sera anonymisé. "
            "Assurez-vous que cela n'affecte pas la lisibilité du document."
        )
    elif coverage < 5:
        recommendations.append(
            f"📊 Seulement {coverage:.1f}% du texte sera anonymisé. "
            "Vérifiez si des entités importantes n'ont pas été manquées."
        )
    
    # Recommandations basées sur les types d'entités
    sensitive_types = ['EMAIL', 'PHONE', 'SSN', 'CREDIT_CARD', 'IBAN']
    found_sensitive = any(entity.get('type') in sensitive_types for entity in entities)
    
    if found_sensitive:
        recommendations.append(
            "🔒 Des données sensibles (emails, téléphones, numéros) ont été détectées. "
            "Assurez-vous de la conformité RGPD."
        )
    
    # Recommandation générale
    if not recommendations:
        recommendations.append("✅ L'anonymisation semble appropriée. Procédez à l'export.")
    
    return recommendations

def create_backup(file_path: str, backup_dir: str = None) -> str:
    """Créer une sauvegarde d'un fichier"""
    try:
        if backup_dir is None:
            backup_dir = Path(file_path).parent / "backups"
        
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(exist_ok=True)
        
        # Nom de la sauvegarde avec timestamp
        original_name = Path(file_path).name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{timestamp}_{original_name}"
        backup_path = backup_dir / backup_name
        
        # Copier le fichier
        shutil.copy2(file_path, backup_path)
        
        logging.info(f"Backup created: {backup_path}")
        return str(backup_path)
        
    except OSError as e:
        # Copying or accessing files may fail if paths are invalid
        logging.error(f"Error creating backup: {str(e)}")
        raise

def compress_file(file_path: str, output_path: str = None) -> str:
    """Compresser un fichier en ZIP"""
    try:
        import zipfile
        
        if output_path is None:
            output_path = f"{file_path}.zip"
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, Path(file_path).name)
        
        logging.info(f"File compressed: {output_path}")
        return output_path
        
    except (OSError, RuntimeError, zipfile.BadZipFile) as e:
        # Compression or file access issues should be surfaced
        logging.error(f"Error compressing file: {str(e)}")
        raise

def validate_entities(entities: List[Dict]) -> List[str]:
    """Valider la structure des entités et retourner les erreurs"""
    errors = []
    required_fields = ['id', 'type', 'value', 'start', 'end']
    
    for i, entity in enumerate(entities):
        # Vérifier les champs requis
        for field in required_fields:
            if field not in entity:
                errors.append(f"Entité {i}: champ '{field}' manquant")
        
        # Vérifier les types de données
        if 'start' in entity and not isinstance(entity['start'], int):
            errors.append(f"Entité {i}: 'start' doit être un entier")
        
        if 'end' in entity and not isinstance(entity['end'], int):
            errors.append(f"Entité {i}: 'end' doit être un entier")
        
        if 'confidence' in entity:
            confidence = entity['confidence']
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                errors.append(f"Entité {i}: 'confidence' doit être entre 0 et 1")
        
        # Vérifier la cohérence des positions
        if ('start' in entity and 'end' in entity and 
            entity['start'] >= entity['end']):
            errors.append(f"Entité {i}: 'start' doit être inférieur à 'end'")
    
    return errors

def format_timestamp(timestamp: datetime = None) -> str:
    """Formater un timestamp pour l'affichage"""
    if timestamp is None:
        timestamp = datetime.now()
    
    return timestamp.strftime("%d/%m/%Y à %H:%M:%S")

def get_system_info() -> Dict[str, Any]:
    """Obtenir des informations système"""
    import platform
    import psutil
    
    try:
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/').percent
        }
    except (psutil.Error, OSError) as e:
        # psutil may fail if system info is unavailable
        logging.error(f"Error getting system info: {str(e)}")
        return {}

def log_processing_metrics(start_time: datetime, entities_count: int, 
                         file_size: int, mode: str) -> None:
    """Logger les métriques de traitement"""
    processing_time = (datetime.now() - start_time).total_seconds()
    
    metrics = {
        "processing_time_seconds": processing_time,
        "entities_detected": entities_count,
        "file_size_bytes": file_size,
        "processing_mode": mode,
        "entities_per_second": entities_count / processing_time if processing_time > 0 else 0,
        "bytes_per_second": file_size / processing_time if processing_time > 0 else 0
    }
    
    logging.info(f"Processing metrics: {json.dumps(metrics, default=str)}")

def ensure_unicode(text: str) -> str:
    """S'assurer que le texte est en Unicode correct"""
    if isinstance(text, bytes):
        # Essayer plusieurs encodages
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                return text.decode(encoding)
            except UnicodeDecodeError:
                continue
        # Si aucun encodage ne fonctionne, utiliser errors='replace'
        return text.decode('utf-8', errors='replace')
    
    return str(text)

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Diviser un texte en chunks avec chevauchement"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Si ce n'est pas le dernier chunk, essayer de couper à un espace
        if end < len(text):
            # Chercher le dernier espace dans les 50 derniers caractères
            last_space = text.rfind(' ', end - 50, end)
            if last_space > start:
                end = last_space
        
        chunks.append(text[start:end])
        
        # Préparer le prochain chunk avec chevauchement
        start = end - overlap if end < len(text) else end
    
    return chunks