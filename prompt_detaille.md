# Prompt détaillé pour la génération d'une application de gestion scolaire

## Contexte du projet

### Présentation de l'établissement
- **Nom**: Lycée Michel ALLAIRE de Ségou
- **Localisation**: Ségou, Mali
- **Contact**:
  - BP: 580
  - Téléphone: 21-32-11-20
  - Téléphone alternatif: 79 07 03 60
  - Email: michelallaire2007@yahoo.fr

### Objectif du projet
Développer une application complète de gestion scolaire permettant de :
1. Gérer les notes et évaluations des élèves
2. Générer des bulletins scolaires personnalisés
3. Administrer les classes et les structures pédagogiques
4. Faciliter la communication entre les acteurs de l'établissement

## Spécifications techniques détaillées

### Architecture globale

#### Backend (API REST)
```
├── src/
│   ├── controllers/          # Logique métier
│   ├── models/              # Modèles de données
│   ├── routes/              # Points d'entrée API
│   ├── middleware/          # Middleware d'authentification
│   ├── services/            # Services métier
│   ├── utils/              # Utilitaires
│   └── config/             # Configuration
```

#### Frontend (Application Web)
```
├── src/
│   ├── components/          # Composants réutilisables
│   ├── pages/              # Pages de l'application
│   ├── layouts/            # Mises en page
│   ├── hooks/              # Hooks personnalisés
│   ├── services/           # Services API
│   ├── store/              # Gestion d'état
│   └── utils/              # Utilitaires
```

### Modèles de données

#### 1. Utilisateur (User)
```typescript
interface User {
  id: number;
  username: string;
  password: string;          // Haché avec bcrypt
  role: 'proviseur' | 'proviseur_adjoint' | 'teacher' | 'student' | 'parent';
  firstName: string;
  lastName: string;
  email?: string;
  phoneNumber?: string;
  dateCreated: Date;
  lastLogin: Date;
  isActive: boolean;
  filiereId?: number;      // Pour les étudiants
  subjects?: string[];       // Pour les enseignants
}
```

#### 2. Filière
```typescript
interface Filiere {
  id: number;
  name: string;             // Format: "[10-12]e (SE|SExp|SEco|SS|LL|S)"
  numberOfPeriods: 2 | 3;   // Nombre de périodes dans l'année
  subjects_group1: {
    name: string;
    coefficient: number;
  }[];
  subjects_group2: {
    name: string;
    coefficient: number;
  }[];
  academicYear: string;     // ex: "2024-2025"
  headTeacherId: number;    // Professeur principal
  createdAt: Date;
  updatedAt: Date;
}
```

#### 3. Note (Grade)
```typescript
interface Grade {
  id: number;
  studentId: number;
  subject: string;
  moyenneClasse: number;    // Note continue (0-20)
  noteComposition: number;  // Note d'examen (0-20)
  coefficient: number;
  appreciation: string;
  period: string;          // ex: "1ère Période"
  teacherId: number;
  createdAt: Date;
  updatedAt: Date;
}
```

#### 4. Structure de Bulletin (BulletinStructure)
```typescript
interface BulletinStructure {
  id: number;
  filiereId: number;
  subjectsGroup1: Subject[];  // Matières principales
  subjectsGroup2: Subject[];  // Matières secondaires
  createdAt: Date;
  updatedAt: Date;
}

interface Subject {
  name: string;
  coefficient: number;
  teacherId: number;
}
```

#### 5. Bulletin (Report)
```typescript
interface Report {
  id: number;
  studentId: number;
  filiereId: number;
  period: string;
  grades: Grade[];
  averages: {
    group1Average: number;    // Moyenne des matières principales
    group2Average: number;    // Moyenne des matières secondaires
    finalAverage: number;     // (group1Average + group2Average) / 2
  };
  classStatistics: {
    minAverage: number;
    maxAverage: number;
    classAverage: number;
  };
  rank: number;
  totalStudents: number;
  appreciation: string;       // Généré automatiquement selon la moyenne finale
  generatedAt: Date;
  proviseurSignature: boolean;
}
```

### Fonctionnalités détaillées

#### 1. Système d'authentification
- **Inscription** :
  ```typescript
  interface RegistrationRequest {
    username: string;
    password: string;
    role: UserRole;
    firstName: string;
    lastName: string;
    email?: string;
    phoneNumber?: string;
    filiereId?: number;     // Pour les étudiants
    teacherCode?: string;   // Pour les enseignants
  }
  ```
- **Connexion** :
  - JWT avec refresh token
  - Sessions persistantes avec `httpOnly` cookies
  - Déconnexion automatique après inactivité

#### 2. Interface Enseignant

##### a. Tableau de bord
- Vue d'ensemble des classes,notes
- Statistiques des notes récentes
- Alertes et notifications
- Calendrier des évaluations

##### b. Gestion des notes
```typescript
// Interface pour la sélection de filière
interface TeacherFiliereSelect {
  teacherId: number;
  filieres: {
    id: number;
    name: string;
    subjects: string[];  // Matières enseignées par le prof dans cette filière
  }[];
}

// Interface pour la saisie des notes
interface GradeEntryGrid {
  filiereId: number;
  subject: string;
  period: string;
  activeColumns: {
    moyenneClasse: boolean;
    noteComposition: boolean;
  };
  students: {
    id: number;
    firstName: string;
    lastName: string;
    moyenneClasse: number;     // Default à 0
    noteComposition: number;    // Default à 0
  }[];
  isDraft: boolean;
}

// Validation des notes
interface GradeValidation {
  min: 0;
  max: 20;
  decimals: 2;  // Permet 12.5, 19.75, etc.
  warningThresholds: {
    low: 5;     // Alerte visuelle pour notes < 5
    high: 19;   // Alerte visuelle pour notes > 19
  };
}

// Props du composant de saisie
interface GradeEntryComponentProps {
  onSubmit: (grades: GradeEntryGrid) => Promise<void>;
  onSaveDraft: (grades: GradeEntryGrid) => void;
  onKeyNavigation: (event: KeyboardEvent, currentCell: { row: number, col: number }) => void;
}
```

##### c. Composant de saisie des notes
```typescript
const GradeEntryTable: React.FC<GradeEntryComponentProps> = ({ onSubmit, onSaveDraft, onKeyNavigation }) => {
  // État local
  const [grades, setGrades] = useState<GradeEntryGrid>({
    filiereId: 0,
    subject: '',
    period: '',
    activeColumns: {
      moyenneClasse: true,
      noteComposition: true
    },
    students: [],
    isDraft: false
  });
  const [isDraft, setIsDraft] = useState(false);
  
  // Validation des notes
  const validateGrade = (value: string): boolean => {
    const num = parseFloat(value);
    if (isNaN(num)) return false;
    if (num < 0 || num > 20) return false;
    const decimals = value.includes('.') ? value.split('.')[1].length : 0;
    return decimals <= 2;
  };

  // Validation du formulaire
  const isFormValid = (): boolean => {
    if (!grades.activeColumns.moyenneClasse && !grades.activeColumns.noteComposition) {
      return false; // Au moins une colonne doit être active
    }

    return grades.students.every(student => {
      if (grades.activeColumns.moyenneClasse && (student.moyenneClasse < 0 || student.moyenneClasse > 20)) {
        return false;
      }
      if (grades.activeColumns.noteComposition && (student.noteComposition < 0 || student.noteComposition > 20)) {
        return false;
      }
      return true;
    });
  };

  // Gestion de la saisie
  const handleGradeChange = (studentId: number, type: 'moyenneClasse' | 'noteComposition', value: string) => {
    if (value === '' || validateGrade(value)) {
      const newGrades = {...grades};
      const student = newGrades.students.find(s => s.id === studentId);
      if (student) {
        student[type] = value === '' ? null : parseFloat(value);
      }
      setGrades(newGrades);
    }
  };

  // Navigation au clavier
  const handleKeyDown = (e: KeyboardEvent, row: number, col: number) => {
    onKeyNavigation(e, { row, col });
  };

  // Style pour les notes extrêmes
  const getGradeStyle = (value: number | null) => {
    if (value === null) return {};
    if (value < 5) return { color: 'red' };
    if (value > 19) return { color: 'orange' };
    return {};
  };

  return (
    <div className="grade-entry-container">
      {/* En-tête avec sélection de filière et matière */}
      <div className="grade-entry-header">
        <FilierePicker teacherId={currentTeacherId} />
        <PeriodPicker />
        
        {/* Options de saisie */}
        <div className="grade-options">
          <label>
            <input
              type="checkbox"
              checked={grades.activeColumns.moyenneClasse}
              onChange={(e) => {
                setGrades({
                  ...grades,
                  activeColumns: {
                    ...grades.activeColumns,
                    moyenneClasse: e.target.checked
                  },
                  students: grades.students.map(s => ({
                    ...s,
                    moyenneClasse: e.target.checked ? s.moyenneClasse : 0
                  }))
                });
              }}
            />
            Notes Devoir
          </label>
          <label>
            <input
              type="checkbox"
              checked={grades.activeColumns.noteComposition}
              onChange={(e) => {
                setGrades({
                  ...grades,
                  activeColumns: {
                    ...grades.activeColumns,
                    noteComposition: e.target.checked
                  },
                  students: grades.students.map(s => ({
                    ...s,
                    noteComposition: e.target.checked ? s.noteComposition : 0
                  }))
                });
              }}
            />
            Notes Composition
          </label>
        </div>
      </div>

      {/* Tableau de saisie */}
      <table className="grade-entry-table">
        <thead>
          <tr>
            <th>Nom</th>
            <th>Prénom</th>
            {grades.activeColumns.moyenneClasse && <th>Note Devoir</th>}
            {grades.activeColumns.noteComposition && <th>Note Composition</th>}
          </tr>
        </thead>
        <tbody>
          {grades.students.map((student, rowIndex) => (
            <tr key={student.id}>
              <td>{student.lastName}</td>
              <td>{student.firstName}</td>
              {grades.activeColumns.moyenneClasse && (
                <td>
                  <input
                    type="number"
                    step="0.25"
                    min="0"
                    max="20"
                    value={student.moyenneClasse}
                    onChange={(e) => handleGradeChange(student.id, 'moyenneClasse', e.target.value || '0')}
                    onKeyDown={(e) => handleKeyDown(e, rowIndex, 0)}
                    style={getGradeStyle(student.moyenneClasse)}
                  />
                </td>
              )}
              {grades.activeColumns.noteComposition && (
                <td>
                  <input
                    type="number"
                    step="0.25"
                    min="0"
                    max="20"
                    value={student.noteComposition}
                    onChange={(e) => handleGradeChange(student.id, 'noteComposition', e.target.value || '0')}
                    onKeyDown={(e) => handleKeyDown(e, rowIndex, 1)}
                    style={getGradeStyle(student.noteComposition)}
                  />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Boutons d'action */}
      <div className="grade-entry-actions">
        <button 
          onClick={() => onSaveDraft(grades)}
          className="draft-button"
        >
          Enregistrer brouillon
        </button>
        <button 
          onClick={() => onSubmit(grades)}
          className="submit-button"
          disabled={!isFormValid()}
        >
          Soumettre les notes
        </button>
      </div>
    </div>
  );
};
```

##### d. Gestion des bulletins
- Création des structures
- Personnalisation des modèles
- Validation multi-niveaux(pour plus tard)
- Export PDF/Excel

#### 3. Interface Étudiant

##### a. Tableau de bord
- Moyennes par matière
- Évolution des notes
- Classement dans la classe
- Notifications

##### b. Visualisation des notes
- Filtrage par période/matière
- Graphiques de progression
- Comparaison avec la moyenne de classe

##### c. Bulletins
- Téléchargement PDF
- Signatures électroniques

#### 4. Calculs et logique métier

##### a. Calcul des moyennes
```typescript
interface GradeCalculation {
  // Moyenne par matière
  calculateSubjectAverage(moyenneClasse: number, noteComposition: number): number {
    return (moyenneClasse + 2 * noteComposition) / 3;
  }

  // Moyenne d'un groupe (principales ou secondaires)
  calculateGroupAverage(grades: Grade[], groupSubjects: Subject[]): number {
    const weightedSum = grades.reduce((sum, grade) => {
      const subject = groupSubjects.find(s => s.name === grade.subject);
      if (!subject) return sum;
      const avg = this.calculateSubjectAverage(grade.moyenneClasse, grade.noteComposition);
      return sum + (avg * subject.coefficient);
    }, 0);
    
    const totalCoeff = groupSubjects.reduce((sum, s) => sum + s.coefficient, 0);
    return weightedSum / totalCoeff;
  }

  // Moyenne finale
  calculateFinalAverage(group1Average: number, group2Average: number): number {
    return (group1Average + group2Average) / 2;
  }
}
```

##### b. Attribution des appréciations
```typescript
function getAppreciation(average: number): string {
  if (average >= 16) return "Très Bien";
  if (average >= 14) return "Bien";
  if (average >= 12) return "Assez Bien";
  if (average >= 10) return "Passable";
  if (average >= 8) return "Insuffisant";
  return "Faible";
}
```

### Interface utilisateur

#### 1. Thème et style
```scss
// Variables
$primary-color: #1a73e8;
$secondary-color: #34a853;
$error-color: #ea4335;
$warning-color: #fbbc04;
$success-color: #0f9d58;

// Typography
$font-family-base: 'Roboto', sans-serif;
$font-size-base: 16px;
$line-height-base: 1.5;

// Breakpoints
$breakpoint-sm: 576px;
$breakpoint-md: 768px;
$breakpoint-lg: 992px;
$breakpoint-xl: 1200px;
```

#### 2. Composants réutilisables

##### a. Tableaux de données
```typescript
interface DataTableProps<T> {
  data: T[];
  columns: Column[];
  sortable?: boolean;
  filterable?: boolean;
  pagination?: {
    pageSize: number;
    currentPage: number;
    totalItems: number;
  };
  onSort?: (column: string, direction: 'asc' | 'desc') => void;
  onFilter?: (filters: Filter[]) => void;
  onPageChange?: (page: number) => void;
}
```

##### b. Formulaires
```typescript
interface FormFieldProps {
  name: string;
  label: string;
  type: 'text' | 'number' | 'email' | 'password' | 'select' | 'date';
  value: any;
  onChange: (value: any) => void;
  validation?: {
    required?: boolean;
    min?: number;
    max?: number;
    pattern?: RegExp;
    custom?: (value: any) => boolean;
  };
  error?: string;
}
```

### Génération de PDF

#### 1. Structure du bulletin
```typescript
interface BulletinTemplate {
  header: {
    schoolName: string;
    schoolInfo: {
      bp: string;
      tel: string;
      email: string;
    };
    logo?: string;
    stamp?: string;
  };
  studentInfo: {
    name: string;
    filiere: string;
    period: string;
  };
  gradesTable: {
    headers: string[];
    rows: GradeRow[];
    groupTotals: GroupTotal[];
  };
  summary: {
    averages: {
      group1Average: number;
      group2Average: number;
      finalAverage: number;
    };
    statistics: {
      minAverage: number;
      maxAverage: number;
      classAverage: number;
    };
    rank: string;
    totalStudents: number;
    appreciation: string;     // Généré automatiquement
    proviseurSignature: boolean;
  };
}
```

#### 2. Styles du bulletin
```typescript
const bulletinStyles = {
  page: {
    margin: 40,
    padding: 20,
    fontFamily: 'Helvetica',
  },
  header: {
    fontSize: 14,
    alignment: 'center',
    marginBottom: 20,
  },
  table: {
    fontSize: 10,
    headerFillColor: '#f0f0f0',
    borderWidth: 1,
    cellPadding: 5,
  },
  summary: {
    fontSize: 12,
    marginTop: 20,
    borderTop: '1px solid #000',
  },
};
```

### Sécurité

#### 1. Protection des données
- Hachage des mots de passe avec bcrypt
- Chiffrement des données sensibles
- Validation des entrées
- Protection contre les injections SQL

#### 2. Authentification
```typescript
interface AuthConfig {
  jwtSecret: string;
  jwtExpiresIn: string;
  refreshTokenExpiresIn: string;
  passwordHashRounds: number;
  sessionTimeout: number;
}
```

#### 3. Autorisation
```typescript
interface Permission {
  resource: string;
  action: 'create' | 'read' | 'update' | 'delete';
}

interface Role {
  name: string;
  permissions: Permission[];
}

const rolePermissions: Record<string, Permission[]> = {
  proviseur: [
    { resource: '*', action: '*' },
    { resource: 'teachers', action: 'manage' }
  ],
  proviseur_adjoint: [
    { resource: '*', action: '*' },
    { resource: 'teachers', action: 'manage' }
  ],
  teacher: [
    { resource: 'grades', action: 'create' },
    { resource: 'grades', action: 'read' },
    { resource: 'grades', action: 'update' },
    { resource: 'bulletins', action: 'create' },
    { resource: 'classes', action: 'read' },
  ],
  student: [
    { resource: 'grades', action: 'read' },
    { resource: 'bulletins', action: 'read' },
  ],
};
```

### API Endpoints

#### 1. Authentification
```typescript
// POST /api/auth/register
interface RegisterResponse {
  user: User;
  token: string;
}

// POST /api/auth/login
interface LoginResponse {
  user: User;
  token: string;
  refreshToken: string;
}

// POST /api/auth/refresh-token
interface RefreshTokenResponse {
  token: string;
}
```

#### 2. Gestion des notes
```typescript
// GET /api/grades/filiere/:filiereId
interface GetFiliereGradesResponse {
  grades: Grade[];
  statistics: {
    average: number;
    highest: number;
    lowest: number;
    distribution: number[];
  };
}

// POST /api/grades/batch
interface BatchGradeResponse {
  success: boolean;
  created: number;
  updated: number;
  errors: string[];
}
```

#### 3. Gestion des bulletins
```typescript
// GET /api/bulletins/generate/:studentId
interface GenerateBulletinResponse {
  bulletinId: number;
  pdfUrl: string;
  generatedAt: Date;
}

// POST /api/bulletins/structure
interface CreateBulletinStructureResponse {
  structure: BulletinStructure;
  message: string;
}
```

### Tests

#### 1. Tests unitaires
```typescript
describe('Grade Calculations', () => {
  test('should calculate subject average correctly', () => {
    const moyenneClasse = 15;
    const noteComposition = 18;
    const expected = 17;
    expect(calculateSubjectAverage(moyenneClasse, noteComposition)).toBe(expected);
  });

  test('should calculate weighted average correctly', () => {
    const grades = [
      { moyenneClasse: 15, noteComposition: 18, coefficient: 5 },
      { moyenneClasse: 12, noteComposition: 14, coefficient: 3 }
    ];
    const expected = 16.25;
    expect(calculateWeightedAverage(grades)).toBe(expected);
  });
});
```

#### 2. Tests d'intégration
```typescript
describe('Grade API', () => {
  test('should create new grades in batch', async () => {
    const grades = [
      { studentId: 1, filiereId: 1, subject: 'MATHS', moyenneClasse: 15, noteComposition: 18 },
      { studentId: 2, filiereId: 1, subject: 'MATHS', moyenneClasse: 12, noteComposition: 14 }
    ];

    const response = await request(app)
      .post('/api/grades/batch')
      .send({ grades })
      .set('Authorization', `Bearer ${token}`);

    expect(response.status).toBe(200);
    expect(response.body.created).toBe(2);
  });
});
```

## Guide de déploiement

### 1. Prérequis
- Node.js >= 14
- PostgreSQL >= 12
- Redis (pour la gestion des sessions)
- Serveur SMTP pour les emails
- Stockage S3 compatible pour les fichiers

### 2. Variables d'environnement
```bash
# Application
NODE_ENV=production
PORT=3000
API_URL=https://api.ecole.com
CLIENT_URL=https://ecole.com

# Base de données
DB_HOST=localhost
DB_PORT=5432
DB_NAME=school_db
DB_USER=school_user
DB_PASSWORD=****

# JWT
JWT_SECRET=****
JWT_EXPIRES_IN=1h
REFRESH_TOKEN_EXPIRES_IN=7d

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=****
SMTP_PASSWORD=****

# Storage
S3_BUCKET=school-files
S3_ACCESS_KEY=****
S3_SECRET_KEY=****
```

### 3. Scripts de déploiement
```json
{
  "scripts": {
    "build": "tsc && webpack --config webpack.prod.js",
    "start": "node dist/server.js",
    "migrate": "prisma migrate deploy",
    "seed": "prisma db seed",
    "test": "jest --coverage",
    "lint": "eslint . --ext .ts",
    "docker:build": "docker build -t school-app .",
    "docker:run": "docker run -p 3000:3000 school-app"
  }
}
```

## Documentation API

### 1. Swagger/OpenAPI
```yaml
openapi: 3.0.0
info:
  title: API de Gestion Scolaire
  version: 1.0.0
  description: API pour la gestion des notes et bulletins

paths:
  /api/grades:
    post:
      summary: Ajouter une note
      tags: [Grades]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GradeInput'
      responses:
        201:
          description: Note créée
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Grade'
```

### 2. Exemples de requêtes
```bash
# Authentification
curl -X POST http://api.ecole.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"teacher1","password":"****"}'

# Ajout de note
curl -X POST http://api.ecole.com/api/grades \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "studentId": 1,
    "subject": "MATHS",
    "moyenneClasse": 15,
    "noteComposition": 18,
    "coefficient": 5
  }'
```

## Maintenance et monitoring

### 1. Logging
```typescript
interface LogConfig {
  level: 'debug' | 'info' | 'warn' | 'error';
  format: 'json' | 'text';
  outputs: ('console' | 'file' | 'external')[];
}

interface LogEntry {
  timestamp: Date;
  level: string;
  message: string;
  context: {
    user?: string;
    action?: string;
    resource?: string;
    error?: any;
  };
}
```

### 2. Métriques
```typescript
interface Metrics {
  activeUsers: number;
  requestsPerMinute: number;
  averageResponseTime: number;
  errorRate: number;
  databaseConnections: number;
  cacheHitRate: number;
}
```

### 3. Alertes
```typescript
interface Alert {
  type: 'error' | 'warning' | 'info';
  message: string;
  timestamp: Date;
  source: string;
  severity: 1 | 2 | 3;
  metadata: Record<string, any>;
}
```