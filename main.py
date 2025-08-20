import streamlit as st
import os
import tempfile
import zipfile
from pathlib import Path
import json
from datetime import datetime
import time
import uuid

# Configuration de la page
st.set_page_config(
    page_title="Anonymiseur de Documents Juridiques",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Imports des modules
from src.anonymizer import DocumentAnonymizer
from src.entity_manager import EntityManager
from src.utils import format_file_size, save_upload_file, cleanup_temp_files
from src.config import ENTITY_COLORS, SUPPORTED_FORMATS, MAX_FILE_SIZE

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .entity-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        margin: 0.1rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        color: white;
    }
    
    .stats-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .success-message {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .error-message {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .processing-animation {
        text-align: center;
        padding: 2rem;
    }
    
    .highlight-text {
        background-color: rgba(255, 255, 0, 0.3);
        padding: 2px 4px;
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialiser les variables de session"""
    if "entities" not in st.session_state:
        st.session_state.entities = []
    if "groups" not in st.session_state:
        st.session_state.groups = []
    if "document_text" not in st.session_state:
        st.session_state.document_text = ""
    if "processing_mode" not in st.session_state:
        st.session_state.processing_mode = "regex"
    if "confidence_threshold" not in st.session_state:
        st.session_state.confidence_threshold = 0.7
    if "processed_file_path" not in st.session_state:
        st.session_state.processed_file_path = None

def display_header():
    """Afficher l'en-tête de l'application"""
    st.markdown("""
    <div class="main-header">
        <h1>🛡️ Anonymiseur de Documents Juridiques</h1>
        <p>Protégez vos documents en anonymisant automatiquement les données sensibles</p>
        <p><strong>Version 2.0 Streamlit</strong> - Conforme RGPD</p>
    </div>
    """, unsafe_allow_html=True)

def display_upload_section():
    """Section d'upload de fichiers"""
    st.header("📁 Upload de Document")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choisissez un document à anonymiser",
            type=SUPPORTED_FORMATS,
            help=f"Formats supportés: {', '.join(SUPPORTED_FORMATS).upper()}. Taille max: {MAX_FILE_SIZE // (1024*1024)} MB"
        )
        
        if uploaded_file:
            # Vérification de la taille
            if uploaded_file.size > MAX_FILE_SIZE:
                st.error(f"❌ Fichier trop volumineux ({format_file_size(uploaded_file.size)}). Taille maximale: {format_file_size(MAX_FILE_SIZE)}")
                return None
            
            # Affichage des informations du fichier
            st.success(f"✅ Fichier sélectionné: **{uploaded_file.name}**")
            st.info(f"📊 Taille: {format_file_size(uploaded_file.size)}")
            
            return uploaded_file
    
    with col2:
        st.markdown("""
        ### 🔧 Modes disponibles
        - **Regex**: Détection rapide (8 types d'entités)
        - **IA**: Détection avancée avec NER
        
        ### 📋 Entités détectées
        - Emails, téléphones, dates
        - Adresses, IBAN, SIREN/SIRET
        - Personnes, organisations (mode IA)
        """)
    
    return None

def display_processing_options():
    """Options de traitement"""
    st.header("⚙️ Options de Traitement")
    
    col1, col2 = st.columns(2)
    
    with col1:
        mode = st.radio(
            "Mode d'analyse",
            ["regex", "ai"],
            format_func=lambda x: "🚀 Regex (Rapide)" if x == "regex" else "🤖 IA (Intelligent)",
            horizontal=True
        )
        st.session_state.processing_mode = mode
    
    with col2:
        if mode == "ai":
            confidence = st.slider(
                "Seuil de confiance",
                min_value=0.1,
                max_value=1.0,
                value=st.session_state.confidence_threshold,
                step=0.1,
                help="Plus le seuil est élevé, plus les détections sont précises mais moins nombreuses"
            )
            st.session_state.confidence_threshold = confidence
        else:
            st.info("💡 Mode Regex: Détection basée sur des patterns prédéfinis")

def process_document(uploaded_file):
    """Traiter le document uploadé"""
    try:
        # Sauvegarde temporaire du fichier
        temp_path = save_upload_file(uploaded_file)
        
        # Création du progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialisation de l'anonymizer
        status_text.text("🔧 Initialisation du traitement...")
        progress_bar.progress(10)
        
        anonymizer = DocumentAnonymizer()
        
        # Analyse du document
        status_text.text("📖 Lecture du document...")
        progress_bar.progress(30)
        
        mode = st.session_state.processing_mode
        confidence = st.session_state.confidence_threshold if mode == "ai" else 0.7
        
        # Traitement
        status_text.text(f"🔍 Analyse en mode {mode.upper()}...")
        progress_bar.progress(60)
        
        result = anonymizer.process_document(temp_path, mode, confidence)
        
        if result["status"] == "success":
            # Mise à jour des données de session
            st.session_state.entities = result["entities"]
            st.session_state.document_text = result["text"]
            st.session_state.processed_file_path = result["anonymized_path"]
            
            status_text.text("✅ Traitement terminé!")
            progress_bar.progress(100)
            
            # Pause pour l'animation
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
            return True
        else:
            st.error(f"❌ Erreur lors du traitement: {result.get('error', 'Erreur inconnue')}")
            return False
            
    except Exception as e:
        st.error(f"❌ Erreur lors du traitement: {str(e)}")
        return False
    finally:
        # Nettoyage
        if 'temp_path' in locals():
            try:
                os.unlink(temp_path)
            except:
                pass

def display_results():
    """Afficher les résultats du traitement"""
    if not st.session_state.entities:
        return
    
    st.header("📊 Résultats de l'Analyse")
    
    # Statistiques
    col1, col2, col3, col4 = st.columns(4)
    
    entity_types = {}
    for entity in st.session_state.entities:
        entity_type = entity["type"]
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    with col1:
        st.metric("Total Entités", len(st.session_state.entities))
    with col2:
        st.metric("Types Différents", len(entity_types))
    with col3:
        st.metric("Mode Utilisé", st.session_state.processing_mode.upper())
    with col4:
        high_confidence = len([e for e in st.session_state.entities if e.get("confidence", 1.0) >= 0.8])
        st.metric("Haute Confiance", high_confidence)
    
    # Répartition par types
    if entity_types:
        st.subheader("🏷️ Répartition par Types")
        
        # Graphique en barres
        import pandas as pd
        df = pd.DataFrame(list(entity_types.items()), columns=['Type', 'Nombre'])
        st.bar_chart(df.set_index('Type'))
        
        # Badges colorés
        st.markdown("### Types détectés:")
        badges_html = ""
        for entity_type, count in entity_types.items():
            color = ENTITY_COLORS.get(entity_type, "#6c757d")
            badges_html += f'<span class="entity-badge" style="background-color: {color};">{entity_type} ({count})</span>'
        st.markdown(badges_html, unsafe_allow_html=True)

def display_entity_manager():
    """Interface de gestion des entités"""
    if not st.session_state.entities:
        return
    
    st.header("🔧 Gestion des Entités")
    
    # Onglets
    tab1, tab2, tab3 = st.tabs(["📝 Entités", "👥 Groupes", "🔍 Recherche"])
    
    with tab1:
        display_entities_tab()
    
    with tab2:
        display_groups_tab()
    
    with tab3:
        display_search_tab()

def display_entities_tab():
    """Onglet de gestion des entités"""
    st.subheader("Liste des Entités Détectées")
    
    # Filtres
    col1, col2 = st.columns([2, 1])
    
    with col1:
        entity_types = list(set([e["type"] for e in st.session_state.entities]))
        selected_types = st.multiselect(
            "Filtrer par type",
            entity_types,
            default=entity_types
        )
    
    with col2:
        show_confidence = st.checkbox("Afficher la confiance", value=True)
    
    # Liste des entités filtrées
    filtered_entities = [e for e in st.session_state.entities if e["type"] in selected_types]
    
    if filtered_entities:
        for i, entity in enumerate(filtered_entities):
            with st.expander(f"{entity['type']}: {entity['value'][:50]}{'...' if len(entity['value']) > 50 else ''}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Valeur:** {entity['value']}")
                    st.write(f"**Type:** {entity['type']}")
                    if show_confidence and "confidence" in entity:
                        confidence_pct = entity['confidence'] * 100
                        st.write(f"**Confiance:** {confidence_pct:.1f}%")
                        st.progress(entity['confidence'])
                    
                    # Modification de la valeur de remplacement
                    new_replacement = st.text_input(
                        "Remplacement personnalisé:",
                        value=entity.get('replacement', f"[{entity['type']}]"),
                        key=f"replacement_{i}"
                    )
                    entity['replacement'] = new_replacement
                
                with col2:
                    if st.button("🗑️ Supprimer", key=f"delete_{i}"):
                        st.session_state.entities.remove(entity)
                        st.rerun()
    else:
        st.info("Aucune entité trouvée avec les filtres sélectionnés.")

def display_groups_tab():
    """Onglet de gestion des groupes"""
    st.subheader("Groupes d'Entités")
    
    # Création d'un nouveau groupe
    with st.expander("➕ Créer un nouveau groupe"):
        group_name = st.text_input("Nom du groupe")
        group_description = st.text_area("Description")
        
        if st.button("Créer le groupe"):
            if group_name:
                new_group = {
                    "id": str(uuid.uuid4()),
                    "name": group_name,
                    "description": group_description,
                    "entities": [],
                    "created_at": datetime.now().isoformat()
                }
                st.session_state.groups.append(new_group)
                st.success(f"✅ Groupe '{group_name}' créé!")
                st.rerun()
    
    # Affichage des groupes existants
    if st.session_state.groups:
        for group in st.session_state.groups:
            with st.expander(f"👥 {group['name']} ({len(group['entities'])} entités)"):
                st.write(f"**Description:** {group.get('description', 'Aucune description')}")
                
                # Sélection d'entités pour le groupe
                available_entities = [
                    f"{e['type']}: {e['value']}" 
                    for e in st.session_state.entities
                ]
                
                selected_entities = st.multiselect(
                    "Entités du groupe:",
                    available_entities,
                    default=[ae for ae in available_entities if ae in group['entities']],
                    key=f"group_entities_{group['id']}"
                )
                
                group['entities'] = selected_entities
                
                if st.button(f"🗑️ Supprimer le groupe", key=f"delete_group_{group['id']}"):
                    st.session_state.groups.remove(group)
                    st.rerun()
    else:
        st.info("Aucun groupe créé. Utilisez le formulaire ci-dessus pour en créer un.")

def display_search_tab():
    """Onglet de recherche"""
    st.subheader("🔍 Recherche dans le Document")
    
    search_term = st.text_input("Rechercher un terme:")
    
    if search_term and st.session_state.document_text:
        # Recherche dans le texte
        text = st.session_state.document_text.lower()
        term = search_term.lower()
        
        if term in text:
            # Compter les occurrences
            count = text.count(term)
            st.success(f"✅ '{search_term}' trouvé {count} fois dans le document")
            
            # Afficher les extraits avec surlignage
            st.subheader("Extraits trouvés:")
            
            lines = st.session_state.document_text.split('\n')
            for i, line in enumerate(lines):
                if term in line.lower():
                    # Surligner le terme trouvé
                    highlighted_line = line.replace(
                        search_term, 
                        f'<span class="highlight-text">{search_term}</span>'
                    )
                    st.markdown(f"**Ligne {i+1}:** {highlighted_line}", unsafe_allow_html=True)
        else:
            st.warning(f"⚠️ '{search_term}' non trouvé dans le document")

def display_export_section():
    """Section d'export"""
    if not st.session_state.processed_file_path:
        return
    
    st.header("📤 Export du Document Anonymisé")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Options d'export
        st.subheader("Options d'Export")
        
        add_watermark = st.checkbox("Ajouter un filigrane", value=True)
        watermark_text = ""
        if add_watermark:
            watermark_text = st.text_input("Texte du filigrane:", value="DOCUMENT ANONYMISÉ")
        
        generate_report = st.checkbox("Générer un rapport d'audit", value=True)
        
        # Bouton d'export
        if st.button("📥 Télécharger le Document Anonymisé", type="primary"):
            try:
                # Lecture du fichier anonymisé
                with open(st.session_state.processed_file_path, 'rb') as f:
                    file_data = f.read()
                
                # Nom du fichier de sortie
                original_name = st.session_state.processed_file_path.split('/')[-1]
                output_name = f"anonymized_{original_name}"
                
                st.download_button(
                    label="💾 Télécharger maintenant",
                    data=file_data,
                    file_name=output_name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
                st.success("✅ Fichier prêt au téléchargement!")
                
            except Exception as e:
                st.error(f"❌ Erreur lors de la préparation du téléchargement: {str(e)}")
    
    with col2:
        # Statistiques d'export
        st.subheader("📊 Statistiques")
        
        total_entities = len(st.session_state.entities)
        st.metric("Entités anonymisées", total_entities)
        
        if total_entities > 0:
            entity_types = {}
            for entity in st.session_state.entities:
                entity_type = entity["type"]
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            st.write("**Répartition:**")
            for entity_type, count in entity_types.items():
                percentage = (count / total_entities) * 100
                st.write(f"- {entity_type}: {count} ({percentage:.1f}%)")

def display_footer():
    """Pied de page de l'application"""
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🛡️ Conformité RGPD")
        st.write("Anonymisation selon les standards CNIL")
    
    with col2:
        st.markdown("### 🔧 Formats Supportés")
        st.write("PDF, DOCX avec préservation du format")
    
    with col3:
        st.markdown("### 📞 Support")
        st.write("Version 2.0 Streamlit - 2024")

def main():
    """Fonction principale de l'application"""
    
    # Initialisation
    init_session_state()
    
    # Nettoyage des fichiers temporaires
    cleanup_temp_files()
    
    # Interface utilisateur
    display_header()
    
    # Sidebar pour la navigation
    with st.sidebar:
        st.title("📋 Navigation")
        
        sections = [
            "📁 Upload",
            "📊 Résultats", 
            "🔧 Gestion",
            "📤 Export"
        ]
        
        selected_section = st.radio("Sections", sections)
        
        st.markdown("---")
        st.markdown("### ℹ️ Informations")
        st.info(f"**Entités détectées:** {len(st.session_state.entities)}")
        st.info(f"**Groupes créés:** {len(st.session_state.groups)}")
    
    # Contenu principal selon la section sélectionnée
    if selected_section == "📁 Upload":
        uploaded_file = display_upload_section()
        
        if uploaded_file:
            display_processing_options()
            
            if st.button("🚀 Lancer l'Analyse", type="primary"):
                with st.spinner("Traitement en cours..."):
                    if process_document(uploaded_file):
                        st.balloons()
                        st.success("🎉 Document traité avec succès!")
                        time.sleep(2)
                        st.rerun()
    
    elif selected_section == "📊 Résultats":
        display_results()
    
    elif selected_section == "🔧 Gestion":
        display_entity_manager()
    
    elif selected_section == "📤 Export":
        display_export_section()
    
    # Pied de page
    display_footer()

if __name__ == "__main__":
    main()