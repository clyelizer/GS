# 🎓 Gestion Scolaire - Lycée Michel ALLAIRE

Application complète de gestion scolaire avec 4 rôles : Admin, Enseignant, Élève, Parent.

---

## 🚀 LANCEMENT SUR GOOGLE COLAB

### Étape 1 : Uploader le projet

1. Ouvrir Google Colab : https://colab.research.google.com
2. Créer un nouveau notebook
3. Monter Google Drive :

```python
from google.colab import drive
drive.mount('/content/drive')
```

4. Uploader le dossier `gestion_scolaire/` dans votre Drive

### Étape 2 : Installer les dépendances

```python
!pip install flask flask-sqlalchemy flask-login flask-migrate reportlab email-validator pyngrok
```

### Étape 3 : Copier les fichiers

```python
import shutil
import os

# Copier depuis Drive vers Colab
src = '/content/drive/MyDrive/gestion_scolaire'  # Adapter le chemin
dst = '/content/gestion_scolaire'

if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(src, dst)

print("✅ Fichiers copiés!")
```

### Étape 4 : Lancer l'application avec ngrok

```python
import os
os.chdir('/content')

# Créer le fichier de lancement
launch_code = '''
from gestion_scolaire import create_app
from pyngrok import ngrok

app = create_app()

# Créer un tunnel public
public_url = ngrok.connect(5000)
print(f"🌐 Application accessible sur: {public_url}")

if __name__ == "__main__":
    app.run(port=5000)
'''

with open('launch.py', 'w') as f:
    f.write(launch_code)

# Lancer (utiliser !python launch.py dans une cellule séparée)
print("Exécutez dans une nouvelle cellule: !python launch.py")
```

### Étape 5 : Exécuter

```python
!python launch.py
```

> 📌 **Note**: ngrok fournira une URL publique (ex: `https://xxxx.ngrok.io`) pour accéder à l'application.

---

## 🔐 COMPTES PAR DÉFAUT

| Rôle | Username | Mot de passe |
|------|----------|--------------|
| 👨‍💼 Admin | `admin` | `admin123` |
| 👨‍🏫 Enseignant | `teacher1` | `teacher123` |
| 👨‍🎓 Élève | (créer via inscription) | - |
| 👨‍👩‍👧 Parent | (créer via inscription) | - |

---

## 📁 STRUCTURE DES FICHIERS

```
gestion_scolaire/
├── __init__.py          # Factory Flask (create_app)
├── app.py               # Configuration app
├── models.py            # Modèles SQLAlchemy (User, Grade, etc.)
├── database.py          # Initialisation DB + données par défaut
├── pdf_generator.py     # Génération bulletins PDF
├── routes/
│   ├── __init__.py
│   ├── auth.py          # Connexion/Inscription
│   ├── main.py          # Redirection dashboard
│   ├── admin.py         # Gestion admin
│   ├── teacher.py       # Interface enseignant
│   ├── student.py       # Interface élève
│   └── parent.py        # Interface parent
├── templates/
│   ├── base.html
│   ├── admin/           # 11 templates admin
│   ├── teacher/         # 4 templates enseignant
│   ├── student/         # 4 templates élève
│   └── parent/          # 6 templates parent
└── static/              # CSS/JS
```

---

## 📋 FONCTIONNALITÉS

### 👨‍💼 Administrateur
- ✅ Gestion des utilisateurs (CRUD)
- ✅ Gestion des classes
- ✅ Gestion des matières
- ✅ Configuration des structures de bulletins
- ✅ Annonces globales
- ✅ Statistiques générales

### 👨‍🏫 Enseignant
- ✅ Saisie des notes par classe/période
- ✅ Gestion des présences
- ✅ Génération des bulletins
- ✅ Visualisation des statistiques

### 👨‍🎓 Élève
- ✅ Consultation des notes
- ✅ Téléchargement du bulletin PDF
- ✅ Historique des présences
- ✅ Moyenne et classement

### 👨‍👩‍👧 Parent
- ✅ Suivi des enfants
- ✅ Consultation des notes
- ✅ Consultation des bulletins
- ✅ Historique des présences
- ✅ Messagerie

---

## 🛠️ DÉPENDANCES

```
flask>=2.3.0
flask-sqlalchemy>=3.0.0
flask-login>=0.6.0
flask-migrate>=4.0.0
reportlab>=3.6.0
email-validator>=2.0.0
```

---

## 📊 BASE DE DONNÉES

L'application utilise SQLite par défaut. Les modèles principaux :

- **User** : Utilisateurs (admin, teacher, student, parent)
- **SchoolClass** : Classes scolaires
- **Subject** : Matières avec coefficients
- **Grade** : Notes des élèves
- **Attendance** : Présences
- **BulletinStructure** : Configuration des bulletins
- **Announcement** : Annonces
- **Message** : Messages parent-école

---

## 🎨 INTERFACE

- Bootstrap 5.3.2
- Font Awesome 6.4.0
- Design responsive
- Thème couleur primaire : `#2c5282` (bleu foncé)

---

**© 2024 Lycée Michel ALLAIRE - Système de Gestion Scolaire**
# School-manager
