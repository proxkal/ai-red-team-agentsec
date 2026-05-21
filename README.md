#  AI Offensive Hackathon : Autonomous LLM Red Team Agent

[![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Agent](https://img.shields.io/badge/Agent-LangGraph-orange.svg)](https://js.langchain.com/docs/langgraph)

Une plateforme d'**Agent IA Offensif Autonome** conçue pour planifier, exécuter et adapter dynamiquement des attaques par injection de prompt (*Prompt Injection* et *Jailbreak*) afin de tester la robustesse et la sécurité des modèles de langage (LLMs).

Contrairement aux outils de scan statiques, cet agent utilise une architecture de **machine à états (State Machine)** pour analyser les échecs de ses tentatives précédentes et ajuster sa stratégie en temps réel jusqu'à l'atteinte de son objectif.

---

##  Aperçu de l'Interface (Dashboard)

![Dashboard de l'Agent Offensif]
*Interface d'administration permettant de configurer la cible, définir l'objectif en langage naturel et suivre l'évolution des campagnes d'attaque autonomes.*

---

##  Fonctionnalités Clés

* **Planification Autonome :** L'agent n'utilise pas de templates statiques. Il analyse l'objectif et l'historique des réponses pour concevoir la meilleure tactique suivante.
* **Génération Dynamique de Payloads :** Mutation et création de prompts d'attaque complexes (obfuscation Unicode, *payload splitting*, usurpation de rôle, attaques de type *DAN*).
* **Analyse de Vulnérabilité par LLM Juge :** Un modèle "Juge" évalue s'il y a eu une véritable fuite d'information (ex: détection d'une vraie clé API vs un faux message de refus).
* **Exécution en Boucle (Stateful Loop) :** Gestion fine du contexte d'attaque via LangGraph avec un mécanisme anti-boucle infinie (*Max Iterations*).
* **Streaming des Pensées (Thought Process) :** Visualisation en temps réel de la stratégie de l'agent et de ses itérations sur le Dashboard.

---

##  Architecture du Système (LangGraph State Machine)

L'agent repose sur une architecture d'état cyclique propulsée par **LangGraph**. L'état de l'agent (`AgentState`) est mis à jour à chaque nœud et guide la transition vers le nœud suivant.

### Les Composants Majeurs :

1.  **Agent State Manager (`agents/state.py`) :** Registre central de mémoire (contient l'objectif, l'historique des payloads tentés, les réponses de la cible, la stratégie actuelle et le score d'impact).
2.  **The Planner Agent (`agents/planner.py`) :** Le cerveau stratégique. Un LLM analyse les échecs passés et choisit le prochain type d'attaque.
3.  **Payload Generator (`agents/generator.py`) :** Reçoit la stratégie du Planner et rédige le prompt d'attaque sur-mesure.
4.  **Vulnerability Analyzer (`analyzer/vulnerability_scanner.py`) :** Un LLM Juge qui inspecte la réponse du modèle cible pour valider (ou non) la réussite de l'objectif.
5.  **Autonomous Loop Engine (`agents/graph.py`) :** Le chef d'orchestre qui relie les nœuds : 
    $$\text{Plan\_Attack} \rightarrow \text{Generate\_Payload} \rightarrow \text{Execute\_Attack} \rightarrow \text{Analyze\_Response}$$
    Si l'objectif est atteint ou si la limite d'itérations est dépassée, le graphe s'arrête (Fin). Sinon, il boucle en adaptant sa logique.

---

##  Stack Technique

* **Backend API :** FastAPI (Python)
* **Orchestration d'Agents :** LangGraph & LangChain
* **LLM Target & Attacker :** Ollama (Mistral 7B exécuté en local)
* **Frontend :** Python (Dashboard interactif via CustomTkinter / Streamlit / Flask - *à ajuster selon ton framework UI*)

---

##  Installation et Démarrage

### 1. Prérequis
Assure-toi d'avoir installé [Ollama](https://ollama.com/) et d'avoir téléchargé le modèle cible :
```bash
ollama run mistral  

---

## 2. Cloner le Projet & Installer les Dépendances
git clone [https://github.com/ton-username/ai-offensive-hackathon.git](https://github.com/ton-username/ai-offensive-hackathon.git)
cd ai-offensive-hackathon
pip install -r requirements.txt

---

### 3. Configurer l'Environnement
Crée un fichier .env à la racine :
OLLAMA_BASE_URL="http://localhost:11434"
# Ajoute tes clés API si tu utilises des modèles distants pour le Planner/Juge (ex: OpenAI, Anthropic)

### 4. Lancer l'Application
Démarre le backend FastAPI :
python main.py

Démarre l'interface graphique :
python dashboard.py

### Flux d'Exécution (Sequence)

[Utilisateur: Objectif] 
       │
       ▼
┌────────────────────────────────────────────────────────┐
│               Boucle Autonome LangGraph                │
│                                                        │
│  ┌──────────────┐      ┌─────────────────────────┐     │
│  │ 1. Planner  │ ───>  │ 2. Payload Generator    │     │
│  └──────────────┘      └─────────────────────────┘     │
│          ▲                          │                  │
│          │                          ▼                  │
│  ┌──────────────┐      ┌─────────────────────────┐     │
│  │ 4. Analyzer  │ <───  │ 3. Target LLM Execution │     │
│  └──────────────┘      └─────────────────────────┘     │
│          │                                             │
└──────────┼─────────────────────────────────────────────┘
           │ (Si Success == True OU Max Iterations)
           ▼
[Fin de la Campagne -> Rapport d'Impact affiché sur l'UI]


Projet développé dans le cadre du Hackathon IA M1 - Agent de Red Teaming Autonome.










