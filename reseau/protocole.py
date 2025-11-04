class Protocole:
    # Dimensions de la grille
    TAILLE_GRILLE = 10

    # Types de messages
    MSG_CONNEXION = "CONNEXION"
    MSG_CONNEXION_OK = "CONNEXION_OK"
    MSG_CHOIX_MODE = "CHOIX_MODE"
    MSG_ATTENTE_ADVERSAIRE = "ATTENTE_ADVERSAIRE"
    MSG_ADVERSAIRE_TROUVE = "ADVERSAIRE_TROUVE"
    MSG_PLACEMENT_BATEAUX = "PLACEMENT_BATEAUX"
    MSG_PLACEMENT_OK = "PLACEMENT_OK"
    MSG_DEBUT_PARTIE = "DEBUT_PARTIE"
    MSG_VOTRE_TOUR = "VOTRE_TOUR"
    MSG_TOUR_ADVERSAIRE = "TOUR_ADVERSAIRE"
    MSG_TIR = "TIR"
    MSG_REPONSE_TIR = "REPONSE_TIR"
    MSG_FIN_PARTIE = "FIN_PARTIE"
    MSG_ABANDON = "ABANDON"
    MSG_ERREUR = "ERREUR"

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

    # États des cases de la grille
    CASE_EAU = 0
    CASE_BATEAU = 1
    CASE_TOUCHE = 2
    CASE_RATE = 3

    # Configuration des bateaux (nom, taille)
    BATEAUX = [
        #("Porte-avions", 5),
        #("Croiseur", 4),
        ("Contre-torpilleur", 3),
        #("Sous-marin", 3),
        #("Torpilleur", 2)
    ]

    # Configuration de l'affichage
    symboles = {
        CASE_EAU: '~',
        CASE_BATEAU: 'B',
        CASE_TOUCHE: 'X',
        CASE_RATE: 'O'
    }

    # Orientations
    HORIZONTAL = "H"
    VERTICAL = "V"

    # Séparateur pour la sérialisation
    SEPARATEUR = "|"

    @staticmethod
    def valider_coordonnees(x, y):
        """Vérifie si les coordonnées sont valides"""

        return 0 <= x < Protocole.TAILLE_GRILLE and 0 <= y < Protocole.TAILLE_GRILLE

    @staticmethod
    def valider_placement(x, y, taille, orientation):
        """Vérifie si un placement de bateau est dans les limites de la grille"""
        if not Protocole.valider_coordonnees(x, y):
            return False

        if orientation == Protocole.HORIZONTAL:
            return x + taille <= Protocole.TAILLE_GRILLE
        elif orientation == Protocole.VERTICAL:
            return y + taille <= Protocole.TAILLE_GRILLE

        return False

    @staticmethod
    def obtenir_symbole_case(valeur_case: int, afficher_bateaux=True):
        """Retourne le symbole d'affichage pour une case"""

        symbole = Protocole.symboles.get(valeur_case, '?')

        if not afficher_bateaux:
            if valeur_case == Protocole.CASE_BATEAU:
                return Protocole.symboles.get(Protocole.CASE_EAU, '~')
        return  symbole

    @staticmethod
    def coordonnees_vers_string(x, y):
        """Convertit des coordonnées en format lisible"""

        lettre = chr(ord('A') + y)
        return f"{lettre}{x}"

    @staticmethod
    def string_vers_coordonnees(coords_str):
        """Convertit un string en coordonnées"""

        try:
            coords_str = coords_str.upper().strip()
            if len(coords_str) < 2:
                return None

            lettre = coords_str[0]
            numero = int(coords_str[1:])

            y = ord(lettre) - ord('A')
            x = numero

            if Protocole.valider_coordonnees(x, y):
                return x, y

            return None
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def obtenir_nombre_total_cases():
        """Calcule le nombre total de cases occupées par tous les bateaux"""

        return sum(taille for _, taille in Protocole.BATEAUX)

    @staticmethod
    def est_resultat_valide(resultat):
        """Vérifie si un résultat de tir est valide"""

        return resultat in [
            Protocole.TIR_RATE,
            Protocole.TIR_TOUCHE,
            Protocole.TIR_DEJA_TIRE,
            Protocole.TIR_COULE
        ]

    @staticmethod
    def est_type_message_valide(type_message):
        """Vérifie si un type de message est valide"""

        return type_message in [
            Protocole.MSG_CONNEXION,
            Protocole.MSG_CONNEXION_OK,
            Protocole.MSG_DEBUT_PARTIE,
            Protocole.MSG_TIR,
            Protocole.MSG_REPONSE_TIR,
            Protocole.MSG_FIN_PARTIE,
            Protocole.MSG_ABANDON,
            Protocole.MSG_ERREUR
        ]

    @staticmethod
    def afficher_regles():
        """Affiche les règles du jeu"""

        print("\n" + "=" * 60)
        print("           RÈGLES DE LA BATAILLE NAVALE")
        print("=" * 60)
        print(f"\n Objectif: Couler tous les bateaux adverses!")
        print(f"\n Grille: {Protocole.TAILLE_GRILLE}x{Protocole.TAILLE_GRILLE}")
        print(f"\n Bateaux à placer:")
        for nom, taille in Protocole.BATEAUX:
            print(f"   - {nom}: {taille} cases")
        print(f"\n Comment jouer:")
        print(f"   - Entrez les coordonnées de tir (ex: 3,5)")
        print(f"   - '~' = Eau")
        print(f"   - 'B' = Votre bateau")
        print(f"   - 'X' = Touché")
        print(f"   - 'O' = Raté")
        print(f"\n Résultats possibles:")
        print(f"   - RATE: Dans l'eau")
        print(f"   - TOUCHE: Bateau touché")
        print(f"   - COULE: Bateau coulé complètement")
        print("\n" + "=" * 60 + "\n")