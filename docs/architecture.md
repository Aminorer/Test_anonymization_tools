# Architecture du Projet

Ce document décrit l'architecture générale de l'anonymiseur ainsi que les
interactions principales entre les composants.

## Diagramme de séquence

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant S as Interface Streamlit
    participant A as DocumentAnonymizer
    participant E as EntityManager

    U->>S: Téléverse un document
    S->>A: `process_document`
    A-->>S: Entités détectées + texte anonymisé
    S->>E: Mise à jour des entités
    E-->>S: Statistiques / Groupes
    U->>S: Demande d'export
    S->>A: `export_anonymized_document`
    A-->>S: Chemins d'export (temp + final)
    S-->>U: Téléchargement
```

## Schéma des modules (`src/`)

```mermaid
graph TD
    subgraph src
        A[config.py]
        B[utils.py]
        C[anonymizer.py]
        D[entity_manager.py]
        E[perf_dashboard.py]
    end

    A --> C
    B --> C
    B --> D
    C --> E
```

- **config.py** : Variables de configuration et constantes.
- **utils.py** : Fonctions utilitaires communes.
- **anonymizer.py** : Cœur de l'anonymisation (regex et IA).
- **entity_manager.py** : Gestion et regroupement des entités détectées.
- **perf_dashboard.py** : Visualisations et métriques de performance.
