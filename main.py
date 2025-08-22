# main.py - VERSION COMPLÈTE AVEC NER FONCTIONNEL
"""
Anonymiseur de Documents Juridiques - Version Streamlit Complète
Avec NER fonctionnel et résolution des conflits PyTorch/Streamlit
"""

# === CONFIGURATION ANTI-CONFLIT PYTORCH/STREAMLIT ===
import os
import sys
import warnings
import logging

# Configuration logging précoce
logging.basicConfig(level=logging.WARNING)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("tensorflow").setLevel(logging.ERROR)

# Variables d'environnement critiques AVANT tous les imports
os.environ.update({
    "TOKENIZERS_PARALLELISM": "false",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1", 
    "OPENBLAS_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "KMP_DUPLICATE_LIB_OK": "TRUE",
    "PYTORCH_JIT": "0",
    "PYTORCH_JIT_USE_NNC": "0"
})

# Suppression des warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*torch.*")
warnings.filterwarnings("ignore", message=".*transformers.*")

# Configuration PyTorch sécurisée AVANT Streamlit
def configure_pytorch_safe():
    """Configuration PyTorch thread-safe pour Streamlit"""
    try:
        import torch
        
        # Configuration threads
        try:
            torch.set_num_threads(1)
        except (RuntimeError, ValueError) as thread_error:
            # Some environments do not support modifying thread settings
            logging.warning(f"PyTorch thread configuration warning: {thread_error}")
        
        # Désactiver JIT et optimisations
        if hasattr(torch.jit, "set_fuser"):
            torch.jit.set_fuser("fuser0")
        torch._C._jit_set_profiling_mode(False)
        torch._C._jit_set_profiling_executor(False)
        
        # Mode évaluation par défaut
        torch.set_grad_enabled(False)
        
        return True
    except (ImportError, RuntimeError, AttributeError) as e:
        # If PyTorch cannot be configured, fall back to regex-only mode
        logging.warning(f"PyTorch configuration warning: {e}")
        return False

# Appliquer la configuration PyTorch AVANT Streamlit
PYTORCH_AVAILABLE = configure_pytorch_safe()

# === IMPORTS STREAMLIT ET MODULES ===
import streamlit as st
import tempfile
import zipfile
from pathlib import Path
import json
from datetime import datetime
import time
import uuid
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import queue

# Configuration Streamlit optimisée
st.set_page_config(
    page_title="Anonymiseur de Documents Juridiques",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Anonymiseur de Documents Juridiques v2.0"
    }
)

# Imports des modules projet
try:
    from src.anonymizer import DocumentAnonymizer
    from src.entity_manager import EntityManager
    from src.utils import (
        format_file_size,
        save_upload_file,
        cleanup_temp_files,
        generate_anonymization_stats,
        calculate_text_coverage,
    )
    from src.config import ENTITY_COLORS, SUPPORTED_FORMATS, MAX_FILE_SIZE, ANONYMIZATION_PRESETS
except ImportError as e:
    st.error(f"❌ Erreur d'import des modules: {e}")
    st.info("Vérifiez que tous les fichiers sont présents dans le dossier src/")
    st.stop()

# === CSS PERSONNALISÉ AMÉLIORÉ ===
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 0.5rem 0;
        opacity: 0.9;
    }
    
    .entity-badge {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        margin: 0.2rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        transition: transform 0.2s ease;
    }
    
    .entity-badge:hover {
        transform: translateY(-2px);
    }
    
    .stats-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    .success-animation {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 2px solid #28a745;
        color: #155724;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(40, 167, 69, 0); }
        100% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0); }
    }
    
    .error-message {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border: 2px solid #dc3545;
        color: #721c24;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
    }
    
    .processing-container {
        text-align: center;
        padding: 3rem;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-radius: 20px;
        margin: 2rem 0;
    }
    
    .processing-spinner {
        width: 60px;
        height: 60px;
        border: 6px solid #e3f2fd;
        border-top: 6px solid #2196f3;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 1rem;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .highlight-text {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        padding: 4px 8px;
        border-radius: 8px;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        border-top: 4px solid #667eea;
    }
    
    .confidence-bar {
        background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
        height: 8px;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    
    .sidebar-info {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .entity-item {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .entity-item:hover {
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    .tab-container {
        background: white;
        border-radius: 15px;
        padding: 1rem;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# === GESTION D'ÉTAT AMÉLIORÉE ===
def init_session_state():
    """Initialiser les variables de session avec valeurs par défaut"""
    defaults = {
        "entities": [],
        "groups": [],
        "document_text": "",
        "processing_mode": "ai",
        "confidence_threshold": 0.7,
        "processed_file_path": None,
        "original_file_path": None,
        "current_preset": "standard",
        "entity_manager": EntityManager(),
        "processing_stats": {},
        "anonymizer": None,
        "last_file_hash": None,
        "export_options": {
            "add_watermark": False,
            "watermark_text": "DOCUMENT ANONYMISÉ - CONFORME RGPD",
            "generate_report": False,
            "include_statistics": False
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_anonymizer():
    """Obtenir ou créer l'anonymizer avec cache"""
    if st.session_state.anonymizer is None:
        st.session_state.anonymizer = DocumentAnonymizer(
            prefer_french=True,
            use_spacy=True
        )
    return st.session_state.anonymizer

# === INTERFACE UTILISATEUR AMÉLIORÉE ===
def display_header():
    """En-tête amélioré avec informations système"""
    st.markdown("""
    <div class="main-header">
        <h1>🛡️ Anonymiseur de Documents Juridiques</h1>
        <p><strong>Intelligence Artificielle</strong> • <strong>Conforme RGPD</strong> • <strong>Haute Précision</strong></p>
        <p>Version 2.0 Professional - Traitement NER Avancé</p>
    </div>
    """, unsafe_allow_html=True)

def display_system_status():
    """Afficher le statut du système"""
    with st.expander("🔧 Statut du Système", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Statut PyTorch
            if PYTORCH_AVAILABLE:
                st.success("✅ PyTorch: Fonctionnel")
            else:
                st.warning("⚠️ PyTorch: Non disponible")
        
        with col2:
            # Statut NER
            try:
                anonymizer = get_anonymizer()
                if anonymizer.ai_anonymizer and anonymizer.ai_anonymizer.spacy_nlp:
                    st.success("✅ NER (SpaCy): Actif")
                elif anonymizer.ai_anonymizer and anonymizer.ai_anonymizer.nlp_pipeline:
                    st.success("✅ NER (Transformers): Actif") 
                else:
                    st.info("ℹ️ NER: Mode Regex uniquement")
            except:
                st.warning("⚠️ NER: Erreur de chargement")
        
        with col3:
            # Mémoire système
            try:
                import psutil
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                if memory_percent < 70:
                    st.success(f"✅ Mémoire: {memory_percent:.1f}%")
                elif memory_percent < 85:
                    st.warning(f"⚠️ Mémoire: {memory_percent:.1f}%")
                else:
                    st.error(f"❌ Mémoire: {memory_percent:.1f}%")
            except:
                st.info("ℹ️ Mémoire: Non disponible")

def display_upload_section():
    """Section d'upload améliorée avec validation"""
    st.header("📁 Upload de Document")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Sélection de preset
        st.subheader("⚙️ Configuration")
        
        preset_options = {
            "light": "🟢 Léger - Données de contact uniquement",
            "standard": "🟡 Standard - Données personnelles principales", 
            "complete": "🔴 Complet - Toutes les données identifiantes",
            "gdpr_compliant": "🛡️ RGPD - Conformité maximale"
        }
        
        selected_preset = st.selectbox(
            "Preset d'anonymisation:",
            options=list(preset_options.keys()),
            format_func=lambda x: preset_options[x],
            index=1,  # Standard par défaut
            key="preset_selector"
        )
        st.session_state.current_preset = selected_preset
        
        # Afficher la description du preset
        if selected_preset in ANONYMIZATION_PRESETS:
            preset_info = ANONYMIZATION_PRESETS[selected_preset]
            st.info(f"📋 {preset_info['description']}")
            
            # Afficher les types d'entités inclus
            types_badges = ""
            for entity_type in preset_info['entity_types']:
                color = ENTITY_COLORS.get(entity_type, "#6c757d")
                types_badges += f'<span class="entity-badge" style="background-color: {color}; font-size: 0.7rem;">{entity_type}</span>'
            st.markdown(f"**Types inclus:** {types_badges}", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Upload de fichier
        uploaded_file = st.file_uploader(
            "Choisissez un document à anonymiser",
            type=SUPPORTED_FORMATS,
            help=f"Formats supportés: {', '.join(SUPPORTED_FORMATS).upper()}. Taille max: {MAX_FILE_SIZE // (1024*1024)} MB",
            key="file_uploader"
        )
        
        if uploaded_file:
            # Validation de la taille
            if uploaded_file.size > MAX_FILE_SIZE:
                st.error(f"❌ Fichier trop volumineux ({format_file_size(uploaded_file.size)}). Maximum autorisé: {format_file_size(MAX_FILE_SIZE)}")
                return None
            
            # Calcul du hash pour détecter les changements
            import hashlib
            file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
            
            # Affichage des informations
            st.success(f"✅ Fichier sélectionné: **{uploaded_file.name}**")
            
            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.metric("Taille", format_file_size(uploaded_file.size))
            with info_col2:
                st.metric("Type", uploaded_file.type.split('/')[-1].upper())
            with info_col3:
                st.metric("Hash", file_hash[:8])
            
            # Détecter si c'est un nouveau fichier
            if file_hash != st.session_state.last_file_hash:
                st.session_state.last_file_hash = file_hash
                st.session_state.entities = []
                st.session_state.processed_file_path = None
                st.info("🔄 Nouveau fichier détecté - Prêt pour analyse")
            
            return uploaded_file
    
    with col2:
        st.subheader("📊 Capacités de Détection")
        
        # Affichage des capacités selon le preset
        if st.session_state.current_preset in ANONYMIZATION_PRESETS:
            preset = ANONYMIZATION_PRESETS[st.session_state.current_preset]
            
            st.markdown("**🎯 Types détectés:**")
            for entity_type in preset['entity_types']:
                color = ENTITY_COLORS.get(entity_type, "#6c757d")
                description = {
                    'EMAIL': '📧 Adresses email',
                    'PHONE': '📞 Numéros de téléphone',
                    'DATE': '📅 Dates', 
                    'ADDRESS': '🏠 Adresses postales',
                    'IBAN': '💳 Comptes bancaires',
                    'SIREN': '🏢 SIREN entreprises',
                    'SIRET': '🏢 SIRET établissements',
                    'PERSON': '👤 Noms de personnes',
                    'ORG': '🏛️ Organisations',
                    'SSN': '🆔 Numéros de sécurité sociale',
                    'CREDIT_CARD': '💳 Cartes bancaires'
                }.get(entity_type, f'📋 {entity_type}')
                
                st.markdown(f'<span style="color: {color};">• {description}</span>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("**🤖 Modes d'analyse:**")
        st.markdown("• **Regex**: Patterns prédéfinis (rapide)")
        st.markdown("• **IA**: NER + Regex (précis)")
        
        st.markdown("**⚡ Performance:**")
        st.markdown("• Regex: ~10-30 secondes")
        st.markdown("• IA: ~1-3 minutes")
    
    return None

def display_processing_options():
    """Options de traitement améliorées"""
    st.header("⚙️ Options de Traitement")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # Mode d'analyse
        mode = st.radio(
            "Mode d'analyse:",
            ["regex", "ai"],
            format_func=lambda x: "🚀 Regex (Rapide)" if x == "regex" else "🤖 IA (Intelligent + Regex)",
            horizontal=True,
            key="processing_mode_radio"
        )
        st.session_state.processing_mode = mode
        
        if mode == "regex":
            st.info("💡 Mode Regex: Détection basée sur des patterns prédéfinis. Rapide et fiable pour les données structurées.")
        else:
            st.info("🧠 Mode IA: Combine NER (reconnaissance d'entités nommées) et patterns regex pour une détection maximale.")
    
    with col2:
        if mode == "ai":
            # Seuil de confiance
            confidence = st.slider(
                "Seuil de confiance IA:",
                min_value=0.1,
                max_value=1.0,
                value=st.session_state.confidence_threshold,
                step=0.05,
                help="Plus le seuil est élevé, plus les détections sont précises mais moins nombreuses",
                key="confidence_slider"
            )
            st.session_state.confidence_threshold = confidence
            
            # Indicateur visuel du seuil
            if confidence >= 0.8:
                st.success(f"🎯 Seuil élevé ({confidence:.0%}) - Haute précision")
            elif confidence >= 0.6:
                st.warning(f"⚖️ Seuil modéré ({confidence:.0%}) - Équilibre précision/rappel")
            else:
                st.error(f"🔍 Seuil bas ({confidence:.0%}) - Détection maximale")
        else:
            st.info("🔧 Mode Regex: Seuil de confiance fixe à 100%")
    
    with col3:
        # Options avancées
        with st.expander("🔧 Avancé"):
            st.checkbox("Mode debug", key="debug_mode", help="Affiche des informations de débogage")
            st.checkbox("Cache résultats", value=True, key="cache_results", help="Met en cache les résultats pour les gros documents")

@st.cache_data(ttl=3600, show_spinner=False)
def process_document_cached(file_content, filename, mode, confidence, preset):
    """Traitement de document avec cache"""
    return process_document_core(file_content, filename, mode, confidence, preset)

def process_document_core(file_content, filename, mode, confidence, preset):
    """Logique de traitement core"""
    # Sauvegarder le fichier temporaire
    temp_path = None
    try:
        import tempfile
        import os

        # Supprimer l'ancien fichier original s'il existe
        old_path = st.session_state.get("original_file_path")
        if old_path and os.path.exists(old_path):
            try:
                os.unlink(old_path)
            except OSError:
                pass

        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            tmp.write(file_content)
            temp_path = tmp.name

        # Conserver le chemin pour l'export ultérieur
        st.session_state["original_file_path"] = temp_path

        # Obtenir l'anonymizer
        anonymizer = get_anonymizer()

        # Traitement avec gestion d'erreurs robuste
        result = anonymizer.process_document(temp_path, mode, confidence, audit=False)

        return result

    except (OSError, ValueError, RuntimeError) as e:
        # Return structured error for file processing issues
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        st.session_state["original_file_path"] = None
        return {
            "status": "error",
            "error": f"Erreur lors du traitement: {str(e)}"
        }

def process_document_with_progress(uploaded_file):
    """Traiter le document avec barre de progression avancée"""
    try:
        # Configuration selon le preset
        preset = ANONYMIZATION_PRESETS.get(st.session_state.current_preset, ANONYMIZATION_PRESETS["standard"])
        
        # Interface de progression
        progress_container = st.empty()
        progress_container.markdown("""
        <div class="processing-container">
            <div class="processing-spinner"></div>
            <h3>🔄 Traitement en cours...</h3>
            <p>Initialisation du système...</p>
        </div>
        """, unsafe_allow_html=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Étapes de traitement
        steps = [
            ("🔧 Initialisation", 10),
            ("📖 Lecture du document", 25),
            ("🧹 Préparation du texte", 35),
            (f"🔍 Analyse {st.session_state.processing_mode.upper()}", 70),
            ("⚡ Finalisation", 90),
            ("✅ Terminé", 100)
        ]
        
        for i, (step_name, progress) in enumerate(steps):
            status_text.text(step_name)
            progress_bar.progress(progress)
            
            if i == 3:  # Étape d'analyse
                # Traitement réel pendant cette étape
                if st.session_state.get("cache_results", True):
                    result = process_document_cached(
                        uploaded_file.getvalue(),
                        uploaded_file.name,
                        st.session_state.processing_mode,
                        st.session_state.confidence_threshold,
                        st.session_state.current_preset
                    )
                else:
                    result = process_document_core(
                        uploaded_file.getvalue(),
                        uploaded_file.name,
                        st.session_state.processing_mode,
                        st.session_state.confidence_threshold,
                        st.session_state.current_preset
                    )
            
            time.sleep(0.3)  # Animation fluide
        
        # Nettoyer l'interface de progression
        progress_container.empty()
        progress_bar.empty()
        status_text.empty()
        
        # Traiter le résultat
        if result["status"] == "success":
            # Filtrer les entités selon le preset
            filtered_entities = []
            for entity in result["entities"]:
                if entity["type"] in preset["entity_types"]:
                    filtered_entities.append(entity)
            
            # Mettre à jour l'état
            st.session_state.entities = filtered_entities
            st.session_state.document_text = result["text"]
            st.session_state.processed_file_path = result.get("anonymized_path")
            st.session_state.processing_stats = result.get("metadata", {})
            
            # Ajouter les entités au gestionnaire
            st.session_state.entity_manager = EntityManager()
            for entity in filtered_entities:
                st.session_state.entity_manager.add_entity(entity)
            
            return True
        else:
            st.error(f"❌ Erreur lors du traitement: {result.get('error', 'Erreur inconnue')}")
            return False
            
    except (OSError, ValueError, RuntimeError) as e:
        # Surface processing errors to the user
        st.error(f"❌ Erreur lors du traitement: {str(e)}")
        if st.session_state.get("debug_mode", False):
            st.exception(e)
        return False

def display_results_advanced():
    """Affichage avancé des résultats"""
    if not st.session_state.entities:
        st.info("Aucun document traité. Uploadez et analysez un document d'abord.")
        return
    
    st.header("📊 Résultats de l'Analyse")
    
    # Statistiques générales
    entities = st.session_state.entities
    stats = generate_anonymization_stats(entities, len(st.session_state.document_text))
    
    # Métriques principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Entités",
            stats["total_entities"],
            help="Nombre total d'entités détectées"
        )
    
    with col2:
        st.metric(
            "Types Différents", 
            len(stats["entity_types"]),
            help="Nombre de types d'entités différents"
        )
    
    with col3:
        mode_display = st.session_state.processing_mode.upper()
        st.metric("Mode", mode_display)
    
    with col4:
        if stats["confidence_stats"]:
            avg_conf = stats["confidence_stats"]["average"]
            st.metric(
                "Confiance Moy.",
                f"{avg_conf:.0%}",
                help="Confiance moyenne des détections IA"
            )
        else:
            st.metric("Confiance", "100%")
    
    with col5:
        coverage = stats["coverage_percentage"]
        st.metric(
            "Couverture",
            f"{coverage:.1f}%",
            help="Pourcentage du texte qui sera anonymisé"
        )
    
    # Graphique de répartition
    if stats["entity_types"]:
        st.subheader("📈 Répartition par Types")
        
        import plotly.express as px
        import pandas as pd
        
        # Préparer les données pour le graphique
        df = pd.DataFrame([
            {"Type": entity_type, "Nombre": count, "Couleur": ENTITY_COLORS.get(entity_type, "#6c757d")}
            for entity_type, count in stats["entity_types"].items()
        ])
        
        # Graphique en barres coloré
        fig = px.bar(
            df, 
            x="Type", 
            y="Nombre",
            color="Type",
            color_discrete_map={row["Type"]: row["Couleur"] for _, row in df.iterrows()},
            title="Distribution des Entités Détectées"
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Graphique camembert
        col1, col2 = st.columns(2)
        
        with col1:
            fig_pie = px.pie(
                df, 
                values="Nombre", 
                names="Type",
                color="Type",
                color_discrete_map={row["Type"]: row["Couleur"] for _, row in df.iterrows()},
                title="Répartition Proportionnelle"
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Tableau détaillé
            st.subheader("📋 Détail par Type")
            total = sum(stats["entity_types"].values())
            
            for entity_type, count in sorted(stats["entity_types"].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total) * 100
                color = ENTITY_COLORS.get(entity_type, "#6c757d")
                
                st.markdown(f"""
                <div style="display: flex; align-items: center; margin: 0.5rem 0;">
                    <span style="width: 20px; height: 20px; background-color: {color}; border-radius: 50%; margin-right: 10px;"></span>
                    <span style="flex: 1;"><strong>{entity_type}</strong>: {count} ({percentage:.1f}%)</span>
                </div>
                """, unsafe_allow_html=True)
    
    # Statistiques de confiance (mode IA)
    if stats["confidence_stats"] and st.session_state.processing_mode == "ai":
        st.subheader("🎯 Analyse de Confiance")
        
        conf_col1, conf_col2, conf_col3 = st.columns(3)
        
        with conf_col1:
            high_conf = stats["confidence_stats"]["high_confidence_count"]
            st.metric("Haute Confiance (≥80%)", high_conf, help="Entités très fiables")
        
        with conf_col2:
            medium_conf = stats["confidence_stats"]["medium_confidence_count"]
            st.metric("Confiance Moyenne (50-80%)", medium_conf, help="Entités moyennement fiables")
        
        with conf_col3:
            low_conf = stats["confidence_stats"]["low_confidence_count"]
            st.metric("Faible Confiance (<50%)", low_conf, help="Entités à vérifier manuellement")
    
    # Recommandations
    if stats["recommendations"]:
        st.subheader("💡 Recommandations")
        for recommendation in stats["recommendations"]:
            if "⚠️" in recommendation:
                st.warning(recommendation)
            elif "🔒" in recommendation:
                st.error(recommendation)
            elif "✅" in recommendation:
                st.success(recommendation)
            else:
                st.info(recommendation)

def display_entity_manager_advanced():
    """Interface avancée de gestion des entités"""
    if not st.session_state.entities:
        st.info("Aucune entité à gérer. Analysez d'abord un document.")
        return
    
    st.header("🔧 Gestion Avancée des Entités")
    
    # Onglets améliorés
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Entités", "👥 Groupes", "🔍 Recherche", "📊 Analyse"])
    
    with tab1:
        display_entities_tab_advanced()
    
    with tab2:
        display_groups_tab_advanced()
    
    with tab3:
        display_search_tab_advanced()
    
    with tab4:
        display_analysis_tab()

def display_entities_tab_advanced():
    """Onglet entités avec fonctionnalités avancées"""
    st.subheader("📝 Gestion des Entités")
    
    # Contrôles de filtrage avancés
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Filtre par type
        entity_types = list(set([e["type"] for e in st.session_state.entities]))
        selected_types = st.multiselect(
            "Filtrer par type:",
            entity_types,
            default=entity_types,
            key="entity_type_filter"
        )
    
    with col2:
        # Filtre par confiance
        if st.session_state.processing_mode == "ai":
            min_confidence = st.slider(
                "Confiance minimale:",
                0.0, 1.0, 0.0, 0.1,
                key="confidence_filter"
            )
        else:
            min_confidence = 0.0
    
    with col3:
        # Tri
        sort_options = {
            "position": "Position dans le texte",
            "type": "Type d'entité", 
            "confidence": "Confiance",
            "value": "Valeur alphabétique"
        }
        sort_by = st.selectbox(
            "Trier par:",
            options=list(sort_options.keys()),
            format_func=lambda x: sort_options[x],
            key="sort_entities"
        )
    
    with col4:
        # Actions en lot
        col4a, col4b = st.columns(2)
        with col4a:
            if st.button("🗑️ Supprimer sélectionnés", key="delete_selected"):
                st.session_state.show_delete_confirmation = True
        with col4b:
            if st.button("📁 Grouper sélectionnés", key="group_selected"):
                st.session_state.show_group_dialog = True
    
    # Filtrer et trier les entités
    filtered_entities = []
    for entity in st.session_state.entities:
        if (entity["type"] in selected_types and 
            entity.get("confidence", 1.0) >= min_confidence):
            filtered_entities.append(entity)
    
    # Tri
    if sort_by == "position":
        filtered_entities.sort(key=lambda x: x.get("start", 0))
    elif sort_by == "type":
        filtered_entities.sort(key=lambda x: x["type"])
    elif sort_by == "confidence":
        filtered_entities.sort(key=lambda x: x.get("confidence", 1.0), reverse=True)
    elif sort_by == "value":
        filtered_entities.sort(key=lambda x: x["value"].lower())
    
    # Affichage des entités avec sélection
    if filtered_entities:
        st.write(f"**{len(filtered_entities)} entités trouvées**")
        
        # Sélection globale
        select_all = st.checkbox("Sélectionner tout", key="select_all_entities")
        
        selected_entities = []
        
        for i, entity in enumerate(filtered_entities):
            # Container pour chaque entité
            with st.container():
                entity_col1, entity_col2 = st.columns([1, 4])
                
                with entity_col1:
                    # Checkbox de sélection
                    is_selected = st.checkbox(
                        "Sélectionner l'entité",
                        value=select_all,
                        key=f"select_entity_{i}_{entity['id']}",
                        label_visibility="collapsed",
                    )
                    if is_selected:
                        selected_entities.append(entity)
                
                with entity_col2:
                    # Informations de l'entité
                    with st.expander(
                        f"{entity['type']}: {entity['value'][:50]}{'...' if len(entity['value']) > 50 else ''}",
                        expanded=False
                    ):
                        # Détails de l'entité
                        detail_col1, detail_col2 = st.columns([2, 1])
                        
                        with detail_col1:
                            st.write(f"**Valeur:** `{entity['value']}`")
                            st.write(f"**Type:** {entity['type']}")
                            st.write(f"**Position:** {entity['start']}-{entity['end']}")
                            
                            if "confidence" in entity and entity["confidence"] is not None:
                                conf_percent = entity["confidence"] * 100
                                st.write(f"**Confiance:** {conf_percent:.1f}%")
                                
                                # Barre de confiance visuelle
                                st.markdown(f"""
                                <div style="background: #e9ecef; border-radius: 10px; height: 20px; margin: 10px 0;">
                                    <div style="background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%); 
                                                width: {conf_percent}%; height: 100%; border-radius: 10px;">
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Contexte si disponible
                            if "context" in entity and entity["context"]:
                                with st.expander("📄 Contexte"):
                                    st.markdown(entity["context"])
                            
                            # Modification du remplacement
                            new_replacement = st.text_input(
                                "Remplacement personnalisé:",
                                value=entity.get('replacement', f"[{entity['type']}]"),
                                key=f"replacement_{i}_{entity['id']}"
                            )
                            
                            if new_replacement != entity.get('replacement'):
                                entity['replacement'] = new_replacement
                                st.session_state.entity_manager.update_entity(
                                    entity['id'], 
                                    {"replacement": new_replacement}
                                )
                        
                        with detail_col2:
                            # Actions individuelles
                            if st.button("🗑️ Supprimer", key=f"delete_{i}_{entity['id']}"):
                                st.session_state.entities.remove(entity)
                                st.session_state.entity_manager.delete_entity(entity['id'])
                                st.rerun()
                            
                            if st.button("📋 Copier valeur", key=f"copy_{i}_{entity['id']}"):
                                st.session_state.clipboard = entity['value']
                                st.success("Copié!")
                            
                            # Badge de type coloré
                            color = ENTITY_COLORS.get(entity['type'], "#6c757d")
                            st.markdown(f"""
                            <span class="entity-badge" style="background-color: {color};">
                                {entity['type']}
                            </span>
                            """, unsafe_allow_html=True)
        
        # Stocker les entités sélectionnées
        st.session_state.selected_entities = selected_entities
        
    else:
        st.info("Aucune entité ne correspond aux critères de filtrage.")

def display_groups_tab_advanced():
    """Onglet groupes avec fonctionnalités avancées"""
    st.subheader("👥 Gestion des Groupes")
    
    # Création de groupe améliorée
    with st.expander("➕ Créer un nouveau groupe", expanded=False):
        group_col1, group_col2 = st.columns(2)
        
        with group_col1:
            group_name = st.text_input("Nom du groupe:", key="new_group_name")
            group_description = st.text_area("Description:", key="new_group_description")
        
        with group_col2:
            # Sélection d'entités pour le groupe
            available_entities = [
                f"{e['type']}: {e['value'][:30]}{'...' if len(e['value']) > 30 else ''}"
                for e in st.session_state.entities
            ]
            
            selected_for_group = st.multiselect(
                "Entités à inclure:",
                available_entities,
                key="entities_for_new_group"
            )
            
            # Templates de groupes
            st.write("**Templates rapides:**")
            if st.button("📧 Groupe Emails"):
                group_name = "Adresses Email"
                group_description = "Toutes les adresses email détectées"
                selected_for_group = [e for e in available_entities if "EMAIL:" in e]
            
            if st.button("👤 Groupe Personnes"):
                group_name = "Personnes"
                group_description = "Noms et identités de personnes"
                selected_for_group = [e for e in available_entities if "PERSON:" in e]
        
        if st.button("✨ Créer le groupe", type="primary"):
            if group_name and selected_for_group:
                # Obtenir les IDs des entités sélectionnées
                entity_ids = []
                for i, entity_display in enumerate(available_entities):
                    if entity_display in selected_for_group:
                        entity_ids.append(st.session_state.entities[i]['id'])
                
                group_id = st.session_state.entity_manager.create_group(
                    group_name, group_description, entity_ids
                )
                
                st.success(f"✅ Groupe '{group_name}' créé avec {len(entity_ids)} entités!")
                st.rerun()
            else:
                st.warning("Veuillez renseigner un nom et sélectionner des entités.")
    
    # Affichage des groupes existants
    groups = st.session_state.entity_manager.groups
    
    if groups:
        st.subheader(f"📁 Groupes Existants ({len(groups)})")
        
        for group in groups:
            with st.expander(f"👥 {group['name']} ({len(group.get('entity_ids', []))} entités)"):
                group_col1, group_col2 = st.columns([2, 1])
                
                with group_col1:
                    st.write(f"**Description:** {group.get('description', 'Aucune description')}")
                    st.write(f"**Créé le:** {group.get('created_at', 'Date inconnue')}")
                    
                    # Entités du groupe
                    group_entities = st.session_state.entity_manager.get_entities_in_group(group['id'])
                    if group_entities:
                        st.write("**Entités dans ce groupe:**")
                        for entity in group_entities:
                            color = ENTITY_COLORS.get(entity['type'], "#6c757d")
                            st.markdown(f"""
                            <div style="margin: 5px 0; padding: 5px; border-left: 3px solid {color}; background: #f8f9fa;">
                                <strong>{entity['type']}</strong>: {entity['value'][:50]}{'...' if len(entity['value']) > 50 else ''}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("Aucune entité dans ce groupe")
                
                with group_col2:
                    # Actions sur le groupe
                    if st.button(f"✏️ Modifier", key=f"edit_group_{group['id']}"):
                        st.session_state.editing_group = group['id']
                    
                    if st.button(f"🗑️ Supprimer", key=f"delete_group_{group['id']}"):
                        st.session_state.entity_manager.delete_group(group['id'])
                        st.success(f"Groupe '{group['name']}' supprimé!")
                        st.rerun()
                    
                    # Statistiques du groupe
                    if group_entities:
                        entity_types = {}
                        for entity in group_entities:
                            entity_type = entity['type']
                            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                        
                        st.write("**Types:**")
                        for entity_type, count in entity_types.items():
                            st.write(f"• {entity_type}: {count}")
    else:
        st.info("Aucun groupe créé. Utilisez le formulaire ci-dessus pour en créer un.")

def display_search_tab_advanced():
    """Onglet recherche avancée"""
    st.subheader("🔍 Recherche Avancée")
    
    search_col1, search_col2 = st.columns([2, 1])
    
    with search_col1:
        # Recherche textuelle
        search_query = st.text_input(
            "Rechercher dans le document:",
            placeholder="Tapez votre recherche...",
            key="search_query"
        )
        
        # Options de recherche
        search_options_col1, search_options_col2 = st.columns(2)
        
        with search_options_col1:
            case_sensitive = st.checkbox("Sensible à la casse", key="case_sensitive")
            whole_words = st.checkbox("Mots entiers uniquement", key="whole_words")
        
        with search_options_col2:
            use_regex = st.checkbox("Recherche par expression régulière", key="use_regex_search")
            search_in_entities = st.checkbox("Rechercher dans les entités", value=True, key="search_entities")
    
    with search_col2:
        # Recherche rapide prédéfinie
        st.write("**Recherches rapides:**")
        
        quick_searches = {
            "📧 Emails": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "📞 Téléphones": r'(?:\+33|0)[1-9](?:[0-9\s.-]{8,})',
            "🏠 Adresses": r'\b\d+\s+[A-Za-z\s]+(?:rue|avenue|boulevard)',
            "💳 IBAN": r'\b[A-Z]{2}\d{2}[A-Z0-9]+\b',
            "👤 Noms": r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        }
        
        for label, pattern in quick_searches.items():
            if st.button(label, key=f"quick_search_{label}"):
                st.session_state.search_query = pattern
                st.session_state.use_regex_search = True
                st.rerun()
    
    # Effectuer la recherche
    if search_query and st.session_state.document_text:
        results = perform_advanced_search(
            st.session_state.document_text,
            search_query,
            case_sensitive,
            whole_words,
            use_regex,
            search_in_entities
        )
        
        if results:
            st.success(f"✅ {len(results)} occurrence(s) trouvée(s)")
            
            # Affichage des résultats
            for i, result in enumerate(results[:10]):  # Limiter à 10 résultats
                with st.expander(f"Résultat {i+1}: Ligne {result['line']}", expanded=i<3):
                    # Texte avec surlignage
                    highlighted_text = result['text'].replace(
                        result['match'],
                        f'<span class="highlight-text">{result["match"]}</span>'
                    )
                    
                    st.markdown(f"**Contexte:** {highlighted_text}", unsafe_allow_html=True)
                    st.write(f"**Position:** {result['start']}-{result['end']}")
                    
                    # Option pour créer une entité depuis la recherche
                    if st.button(f"➕ Créer entité", key=f"create_entity_{i}"):
                        new_entity = {
                            "id": str(uuid.uuid4()),
                            "type": "SEARCH_RESULT",
                            "value": result['match'],
                            "start": result['start'],
                            "end": result['end'],
                            "confidence": 1.0,
                            "replacement": f"[TROUVÉ]"
                        }
                        st.session_state.entities.append(new_entity)
                        st.session_state.entity_manager.add_entity(new_entity)
                        st.success("Entité créée depuis la recherche!")
                        st.rerun()
            
            if len(results) > 10:
                st.info(f"Seuls les 10 premiers résultats sont affichés. Total: {len(results)}")
        else:
            st.warning("Aucun résultat trouvé.")

def perform_advanced_search(text, query, case_sensitive, whole_words, use_regex, search_entities):
    """Effectuer une recherche avancée dans le texte"""
    import re
    
    results = []
    
    try:
        # Préparer la requête
        if use_regex:
            pattern = query
        else:
            # Échapper les caractères spéciaux regex
            pattern = re.escape(query)
            
            if whole_words:
                pattern = r'\b' + pattern + r'\b'
        
        # Flags de recherche
        flags = 0 if case_sensitive else re.IGNORECASE
        
        # Recherche dans le texte
        lines = text.split('\n')
        char_offset = 0
        
        for line_num, line in enumerate(lines, 1):
            try:
                for match in re.finditer(pattern, line, flags):
                    results.append({
                        'line': line_num,
                        'text': line,
                        'match': match.group(),
                        'start': char_offset + match.start(),
                        'end': char_offset + match.end()
                    })
            except re.error:
                # Pattern regex invalide
                break
            
            char_offset += len(line) + 1  # +1 pour le \n
        
        # Recherche dans les entités si activée
        if search_entities and st.session_state.entities:
            for entity in st.session_state.entities:
                entity_text = f"{entity['type']}: {entity['value']}"
                if (case_sensitive and query in entity_text) or \
                   (not case_sensitive and query.lower() in entity_text.lower()):
                    results.append({
                        'line': 'Entité',
                        'text': entity_text,
                        'match': query,
                        'start': entity.get('start', 0),
                        'end': entity.get('end', 0),
                        'entity_id': entity['id']
                    })
    
    except ValueError as e:
        # Handle invalid search parameters
        st.error(f"Erreur lors de la recherche: {e}")
    
    return results

def display_analysis_tab():
    """Onglet d'analyse statistique avancée"""
    st.subheader("📊 Analyse Statistique Avancée")
    
    if not st.session_state.entities:
        st.info("Aucune donnée à analyser.")
        return
    
    # Statistiques globales
    stats = st.session_state.entity_manager.get_statistics()
    
    # Métriques avancées
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Entités Totales", stats['total_entities'])
        st.metric("Types Uniques", len(stats['entity_types']))
        if stats['most_common_type']:
            st.metric("Type Dominant", stats['most_common_type'])
    
    with col2:
        if stats['confidence_stats']:
            st.metric("Confiance Moyenne", f"{stats['confidence_stats'].get('average', 0):.0%}")
            st.metric("Confiance Minimale", f"{stats['confidence_stats']['min']:.0%}")
            st.metric("Confiance Maximale", f"{stats['confidence_stats']['max']:.0%}")
    
    with col3:
        doc_length = len(st.session_state.document_text)
        entity_density = (stats['total_entities'] / doc_length * 1000) if doc_length > 0 else 0
        st.metric("Densité", f"{entity_density:.1f}/1k chars")

        coverage_percent = calculate_text_coverage(st.session_state.entities, doc_length)
        st.metric("Couverture", f"{coverage_percent:.1f}%")
    
    # Analyse de distribution
    st.subheader("📈 Distribution et Tendances")
    
    # Graphique de distribution des types
    if stats['entity_types']:
        import plotly.graph_objects as go
        
        # Graphique radar des types d'entités
        categories = list(stats['entity_types'].keys())
        values = list(stats['entity_types'].values())
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Distribution des Entités',
            line_color='rgb(102, 126, 234)'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(values)]
                )),
            title="Distribution Radiale des Types d'Entités",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Analyse de confiance (si mode IA)
    if st.session_state.processing_mode == "ai" and stats['confidence_stats']:
        st.subheader("🎯 Analyse de Confiance Détaillée")
        
        confidence_col1, confidence_col2 = st.columns(2)
        
        with confidence_col1:
            # Distribution de confiance
            confidence_values = [e.get('confidence', 1.0) for e in st.session_state.entities if 'confidence' in e]
            
            if confidence_values:
                import plotly.express as px
                
                fig_hist = px.histogram(
                    x=confidence_values,
                    nbins=20,
                    title="Distribution des Niveaux de Confiance",
                    labels={'x': 'Confiance', 'y': 'Nombre d\'entités'}
                )
                fig_hist.update_layout(height=400)
                st.plotly_chart(fig_hist, use_container_width=True)
        
        with confidence_col2:
            # Confiance par type
            confidence_by_type = {}
            for entity in st.session_state.entities:
                if 'confidence' in entity:
                    entity_type = entity['type']
                    if entity_type not in confidence_by_type:
                        confidence_by_type[entity_type] = []
                    confidence_by_type[entity_type].append(entity['confidence'])
            
            if confidence_by_type:
                avg_confidence_by_type = {
                    entity_type: sum(confidences) / len(confidences)
                    for entity_type, confidences in confidence_by_type.items()
                }
                
                fig_bar = px.bar(
                    x=list(avg_confidence_by_type.keys()),
                    y=list(avg_confidence_by_type.values()),
                    title="Confiance Moyenne par Type",
                    labels={'x': 'Type d\'entité', 'y': 'Confiance moyenne'}
                )
                fig_bar.update_layout(height=400)
                st.plotly_chart(fig_bar, use_container_width=True)
    
    # Détection de conflits et anomalies
    st.subheader("⚠️ Détection d'Anomalies")
    
    conflicts = st.session_state.entity_manager.get_entity_conflicts()
    if conflicts:
        st.warning(f"🔍 {len(conflicts)} conflit(s) détecté(s) entre entités")
        
        with st.expander("Voir les conflits"):
            for i, conflict in enumerate(conflicts):
                st.write(f"**Conflit {i+1}:**")
                st.write(f"• Entité 1: {conflict['entity1']['type']} - '{conflict['entity1']['value']}'")
                st.write(f"• Entité 2: {conflict['entity2']['type']} - '{conflict['entity2']['value']}'")
                st.write(f"• Chevauchement: {conflict['overlap_length']} caractères")
                
                if st.button(f"🔧 Résoudre automatiquement", key=f"resolve_conflict_{i}"):
                    resolved = st.session_state.entity_manager.resolve_entity_conflicts("keep_highest_confidence")
                    st.success(f"✅ {resolved} conflit(s) résolu(s)")
                    st.rerun()
    else:
        st.success("✅ Aucun conflit détecté entre les entités")
    
    # Validation de l'intégrité
    integrity_issues = st.session_state.entity_manager.validate_data_integrity()
    if integrity_issues:
        st.error(f"❌ {len(integrity_issues)} problème(s) d'intégrité détecté(s)")
        with st.expander("Voir les problèmes"):
            for issue in integrity_issues:
                st.write(f"• {issue}")
    else:
        st.success("✅ Intégrité des données vérifiée")

def display_export_section_advanced():
    """Section d'export avancée"""
    if not st.session_state.entities:
        st.info("Aucun document à exporter. Analysez d'abord un document.")
        return
    
    st.header("📤 Export du Document Anonymisé")
    
    # Options d'export
    export_col1, export_col2 = st.columns([2, 1])
    
    with export_col1:
        st.subheader("⚙️ Options d'Export")
        
        # Filigrane
        add_watermark = st.checkbox(
            "Ajouter un filigrane",
            value=st.session_state.export_options["add_watermark"],
            key="export_watermark"
        )

        st.session_state.export_options["add_watermark"] = add_watermark
        
        if add_watermark:
            watermark_text = st.text_input(
                "Texte du filigrane:",
                value=st.session_state.export_options["watermark_text"],
                key="watermark_text"
            )
            st.session_state.export_options["watermark_text"] = watermark_text
        
        # Rapport d'audit
        generate_report = st.checkbox(
            "Générer un rapport d'audit complet",
            value=st.session_state.export_options["generate_report"],
            key="export_report"
        )

        st.session_state.export_options["generate_report"] = generate_report
        
        # Statistiques
        include_stats = st.checkbox(
            "Inclure les statistiques détaillées",
            value=st.session_state.export_options["include_statistics"],
            key="export_stats"
        )

        st.session_state.export_options["include_statistics"] = include_stats
        
        # Format d'export
        export_format = st.selectbox(
            "Format d'export:",
            ["docx", "pdf", "txt"],
            format_func=lambda x: {
                "docx": "📄 Word Document (DOCX)",
                "pdf": "📋 PDF Document",
                "txt": "📝 Texte Simple (TXT)"
            }[x]
        )
        
        # Vérifier la présence du fichier original avant export
        original_path = st.session_state.get("original_file_path")
        has_original = isinstance(original_path, str) and original_path.strip()

        if not has_original:
            st.warning("Aucun document original trouvé. Veuillez téléverser ou réanalyser un document avant l'export.")

        export_clicked = st.button(
            "📥 Exporter le document",
            type="primary",
            disabled=not has_original
        )

        if export_clicked and has_original:
            try:
                # Préparer les options d'export
                export_options = {
                    "format": export_format,
                    "watermark": watermark_text if add_watermark else None,
                }
                audit_flag = generate_report or include_stats

                # Exporter en utilisant le fichier original
                anonymizer = get_anonymizer()
                result = anonymizer.export_anonymized_document(
                    original_path,
                    st.session_state.entities,
                    export_options,
                    audit=audit_flag,
                )

                # Téléchargement
                if result and os.path.exists(result):
                    with open(result, "rb") as f:
                        file_content = f.read()

                    file_name = f"anonymized_{Path(original_path).stem}.{export_format}"
                    st.download_button(
                        "⬇️ Télécharger le document anonymisé",
                        file_content,
                        file_name=file_name,
                        mime=f"application/{export_format}"
                    )
                else:
                    st.error("❌ Erreur lors de l'export du document")

            except (OSError, RuntimeError, ValueError) as e:
                # Export may fail due to filesystem or document issues
                st.error(f"❌ Erreur: {str(e)}")
            finally:
                # Nettoyer le fichier original après l'export
                if original_path and os.path.exists(original_path):
                    try:
                        os.unlink(original_path)
                    except OSError:
                        pass
                st.session_state["original_file_path"] = None
    
    with export_col2:
        st.subheader("📊 Résumé de l'Export")
        
        # Informations sur le document
        st.info(f"""
        **Document source:** {Path(st.session_state.processed_file_path).name}
        
        **Format de sortie:** {export_format.upper()}
        
        **Entités à anonymiser:** {len(st.session_state.entities)}
        
        **Options activées:**
        {"• Filigrane" if add_watermark else ""}
        {"• Rapport d'audit" if generate_report else ""}
        {"• Statistiques" if include_stats else ""}
        """)
        
        # Aperçu rapide
        with st.expander("👁️ Aperçu"):
            st.write("Exemple de texte anonymisé:")
            sample_text = st.session_state.document_text[:500]
            for entity in st.session_state.entities:
                if entity['start'] < 500:
                    replacement = entity.get('replacement', f"[{entity['type']}]")
                    sample_text = (
                        sample_text[:entity['start']] +
                        f"**{replacement}**" +
                        sample_text[entity['end']:]
                    )
            st.markdown(f"{sample_text}...")

# === PROGRAMME PRINCIPAL ===
def main():
    """Programme principal"""
    try:
        # Initialisation
        init_session_state()
        
        # En-tête
        display_header()
        display_system_status()
        
        # Upload de fichier
        uploaded_file = display_upload_section()
        
        if uploaded_file:
            # Options de traitement
            display_processing_options()
            
            # Bouton de traitement
            if st.button("🔍 Analyser le Document", type="primary"):
                success = process_document_with_progress(uploaded_file)
                
                if success:
                    st.balloons()
                    st.success("✅ Document analysé avec succès!")
            
            # Afficher les résultats si disponibles
            if st.session_state.entities:
                display_results_advanced()
                display_entity_manager_advanced()
                display_export_section_advanced()
        
        # Nettoyage périodique
        cleanup_temp_files()
        
    except (OSError, ValueError, RuntimeError) as e:
        # Catch any remaining unexpected errors and display them
        st.error(f"❌ Erreur inattendue: {str(e)}")
        if st.session_state.get("debug_mode", False):
            st.exception(e)

if __name__ == "__main__":
    main()