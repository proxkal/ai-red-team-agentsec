# Utiliser une image de base Python officielle et légère
FROM python:3.10-slim

# Définir le dossier de travail dans le conteneur
WORKDIR /app

# Installer les dépendances système nécessaires si besoin (ex: git, curl, build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier le fichier requirements.txt
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY . .

# Exposer le port de l'API FastAPI
EXPOSE 8000

# Commande par défaut pour lancer l'API backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
