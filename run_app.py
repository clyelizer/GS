#!/usr/bin/env python3
"""
Gestion Scolaire - Lycée Michel ALLAIRE
Point d'entrée principal pour l'application CLI
"""

import os
from gestion_scolaire.app import create_app
from gestion_scolaire.database import init_db

def main():
    """Point d'entrée principal pour l'application CLI"""
    # Configuration de l'environnement
    os.environ.setdefault('FLASK_APP', 'gestion_scolaire.app')
    os.environ.setdefault('FLASK_ENV', 'development')
    
    # Initialiser la base de données si nécessaire
    if not os.path.exists('school.db'):
        print("Initialisation de la base de données...")
        app = create_app()
        with app.app_context():
            init_db(app)
    
    # Créer et lancer l'application
    app = create_app()
    
    print("🎓 Gestion Scolaire - Lycée Michel ALLAIRE")
    print("🌐 Serveur démarré sur http://localhost:5000")
    print("👨‍💼 Compte enseignant: teacher / password123")
    print("🔧 Pour arrêter: Ctrl+C")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()