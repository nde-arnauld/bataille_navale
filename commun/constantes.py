
# Dimensions de la grille
TAILLE_GRILLE = 10

# Configuration du système de sauvegarde
FICHIER_SAUVEGARDE_UTILISATEURS = "donnees_utilisateurs.json"
TAILLE_MIN_MDP = 4
ENCODAGE = "utf-8"

# ----------------------------------------------------------------------
# CONFIGURATION DES NAVIRES
# ----------------------------------------------------------------------

# Configuration des bateaux (nom, taille)
NAVIRES = [
    # ("Porte-avions", 5),
    # ("Croiseur", 4),
    # ("Contre-torpilleur", 3),
    # ("Sous-marin", 3),
    ("Torpilleur", 2)
]

# Orientations
HORIZONTAL = "H"
VERTICAL = "V"

# ----------------------------------------------------------------------
# CONFIGURATION RÉSEAU
# ----------------------------------------------------------------------

# Configuration authentification
PORT_AUTH = 5554  # Port UDP pour l'authentification
PORT_JEU = 5555  # Port TCP pour le jeu
NB_MAX_CONNEXIONS = 5

# Taille de l'entête en octets (4 octets = max 4 GB, suffisant ici)
TAILLE_ENTETE = 4

SEPARATEUR = "|" # Séparateur pour la sérialisation

# Entity
CLIENT = "CLIENT"
SERVEUR_AUTH = "SERVEUR_AUTH"
SERVEUR = "SERVEUR"

# ----------------------------------------------------------------------
# TYPES DE MESSAGES ET COMMANDES
# ----------------------------------------------------------------------

# Messages de connexion/déconnexion/base
MSG_CONNEXION = "CONNEXION"
MSG_CONNEXION_OK = "CONNEXION_OK"
MSG_DECONNEXION = "DECONNEXION"
MSG_ERREUR = "ERREUR"

# Messages d'authentification (UDP)
MSG_AUTH_LOGIN = "AUTH_LOGIN"
MSG_AUTH_REGISTER = "AUTH_REGISTER"
MSG_AUTH_SUCCESS = "AUTH_SUCCESS"
MSG_AUTH_FAILED = "AUTH_FAILED"

# Messages de jeu
MSG_CHOIX_MODE = "CHOIX_MODE"
MSG_ATTENTE_ADVERSAIRE = "ATTENTE_ADVERSAIRE"
MSG_ADVERSAIRE_TROUVE = "ADVERSAIRE_TROUVE"
MSG_PLACEMENT_NAVIRES = "PLACEMENT_NAVIRES"
MSG_PLACEMENT_OK = "PLACEMENT_OK"
MSG_DEBUT_PARTIE = "DEBUT_PARTIE"
MSG_VOTRE_TOUR = "VOTRE_TOUR"
MSG_TOUR_ADVERSAIRE = "TOUR_ADVERSAIRE"
MSG_TIR = "TIR"
MSG_REPONSE_TIR = "REPONSE_TIR"
MSG_REPONSE_TIR_RECU = "REPONSE_TIR_RECU"
MSG_FIN_PARTIE = "FIN_PARTIE"
MSG_ABANDON = "ABANDON"

# Messages de chat
MSG_CHAT = "CHAT"
MSG_CHAT_GLOBAL = "CHAT_GLOBAL"

# Messages de sauvegarde/reprise
MSG_PARTIE_SAUVEGARDEE_EXISTE = "PARTIE_SAUVEGARDEE_EXISTE"
MSG_REPRENDRE_PARTIE = "REPRENDRE_PARTIE"
MSG_NOUVELLE_PARTIE = "NOUVELLE_PARTIE"
MSG_PARTIE_REPRISE = "PARTIE_REPRISE"
MSG_SAUVEGARDER_PARTIE = "SAUVEGARDER_PARTIE" # Ajouté pour déclencher la sauvegarde

# ----------------------------------------------------------------------
# ÉTATS ET RÉSULTATS DU JEU
# ----------------------------------------------------------------------

# Nom serveur IA
NOM_SERVEUR = "SERVEUR_IA"

# Modes de jeu
MODE_VS_SERVEUR = "VS_SERVEUR"
MODE_VS_JOUEUR = "VS_JOUEUR"

# Résultats de tir
TIR_RATE = "RATE"
TIR_TOUCHE = "TOUCHE"
TIR_COULE = "COULE"
TIR_DEJA_TIRE = "DEJA TIRE"

# États de partie
ETAT_EN_ATTENTE = "EN_ATTENTE"
ETAT_EN_COURS = "EN_COURS"
ETAT_TERMINEE = "TERMINEE"
ETAT_ABANDONNEE = "ABANDONNEE"
ETAT_MIS_EN_PAUSE = "MIS_EN_PAUSE"

# États des cases de la grille
CASE_EAU = 0
CASE_NAVIRE = 1
CASE_TOUCHE = 2
CASE_RATE = 3

# Quitter la partie
PARTIE_ABANDONNEE = -1
PARTIE_DECONNECTEE = -2

# Configuration de l'affichage
symboles = {
    CASE_EAU: '~',
    CASE_NAVIRE: 'B',
    CASE_TOUCHE: 'X',
    CASE_RATE: 'O'
}

# ----------------------------------------------------------------------
# CONFIGURATION DE L'INTERFACE UTILISATEUR (InterfaceConsole)
# ----------------------------------------------------------------------

# Commande de sortie/arrêt
CMD_QUITTER = "QUITTER"
CMD_CHAT = "CHAT"
CMD_SAUVEGARDER = "SAVE"
CMD_ABANDONNER = "QUIT" # Utilise QUIT car il envoie MSG_ABANDON

# Statuts de connexion/jeu local
STATUS_HORS_LIGNE = "Hors ligne"
STATUS_CONNECTE = "Connecté"

# Options de Menu Principal (Login/Register/Quitter)
CHOIX_MENU_CONNEXION = "1"
CHOIX_MENU_INSCRIPTION = "2"
CHOIX_MENU_QUITTER = "3"

# Options de mode de jeu
CHOIX_MODE_SOLO = "1"
CHOIX_MODE_PVP = "2"

#Options de reprise de la partie
CHOIX_REPRENDRE_PARTIE = "1"
CHOIX_NOUVELLE_PARTIE = "2"

# Options de Placement des Navires
CHOIX_PLACEMENT_MANUEL = "1"
CHOIX_PLACEMENT_AUTO = "2"