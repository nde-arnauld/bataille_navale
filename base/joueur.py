import random
from base.bateau import Bateau
from reseau.protocole import Protocole

class Joueur:
    def __init__(self, nom="Joueur"):
        """
        Initialise un joueur avec ses grilles

        Args:
            nom: Nom du joueur
        """
        self.nom = nom
        # Grille principale (où sont placés les bateaux du joueur)
        self.grille = [[Protocole.CASE_EAU for _ in range(Protocole.TAILLE_GRILLE)]
                       for _ in range(Protocole.TAILLE_GRILLE)]

        # Grille de suivi (pour tracer les tirs effectués sur l'adversaire)
        self.grille_suivi = [[Protocole.CASE_EAU for _ in range(Protocole.TAILLE_GRILLE)]
                             for _ in range(Protocole.TAILLE_GRILLE)]

        # Liste des bateaux
        self.bateaux = []
        self._initialiser_bateaux()

    def _initialiser_bateaux(self):
        """Initialise la liste des bateaux selon le protocole"""
        for nom, taille in Protocole.BATEAUX:
            self.bateaux.append(Bateau(nom, taille))

    def placement_valide(self, bateau, x, y, orientation):
        """
        Vérifie si le placement d'un bateau est valide

        Returns:
            True si le placement est valide, False sinon
        """
        # Vérifier que le bateau ne dépasse pas de la grille
        if orientation == Protocole.HORIZONTAL:
            if x + bateau.taille > Protocole.TAILLE_GRILLE:
                return False
        else:  # VERTICAL
            if y + bateau.taille > Protocole.TAILLE_GRILLE:
                return False

        # Vérifier qu'aucune case n'est déjà occupée
        for i in range(bateau.taille):
            pos_x = x + i if orientation == Protocole.HORIZONTAL else x
            pos_y = y if orientation == Protocole.HORIZONTAL else y + i

            if self.grille[pos_y][pos_x] != Protocole.CASE_EAU:
                return False

        return True

    def placement_manuel_interactif(self):
        """
        Permet au joueur de placer ses bateaux manuellement
        Demande ligne, colonne et orientation séparément
        """
        print("\n=== PLACEMENT DE VOS BATEAUX ===")
        print("Orientation: H (horizontal) ou V (vertical)\n")

        for nom, taille in Protocole.BATEAUX:
            place = False

            while not place:
                # Afficher la grille actuelle
                self.afficher_grille(afficher_bateaux=True)

                print(f"\n{nom} ({taille} cases)")

                try:
                    # Demander la ligne
                    ligne = input("Ligne (0-9): ").strip()
                    if ligne.lower() == 'auto':
                        if self._placer_bateau_aleatoire_unique(nom, taille):
                            print(f"{nom} placé automatiquement")
                            place = True
                        continue

                    y = int(ligne)

                    # Demander la colonne
                    colonne = input("Colonne (0-9): ").strip()
                    x = int(colonne)

                    # Demander l'orientation
                    orientation = input("Orientation (H/V): ").strip().upper()

                    # Validation
                    if not Protocole.valider_coordonnees(x, y):
                        print("Coordonnées invalides!")
                        continue

                    if orientation not in [Protocole.HORIZONTAL, Protocole.VERTICAL]:
                        print("Orientation invalide! Utilisez H ou V")
                        continue

                    # Tenter le placement
                    bateau = Bateau(nom, taille)
                    if self.placer_bateau(bateau, x, y, orientation):
                        print(f"{nom} placé avec succès!")
                        place = True
                    else:
                        print("Placement impossible (hors grille ou collision)")

                except ValueError:
                    print("Erreur de saisie! Utilisez des nombres pour ligne et colonne")
                except Exception as e:
                    print(f"Erreur: {e}")

        print("\n=== PLACEMENT TERMINÉ ===")
        self.afficher_grille(afficher_bateaux=True)

    def _placer_bateau_aleatoire_unique(self, nom, taille):
        """
        Place un seul bateau de manière aléatoire
        """
        for _ in range(1000):
            x = random.randint(0, Protocole.TAILLE_GRILLE - 1)
            y = random.randint(0, Protocole.TAILLE_GRILLE - 1)
            orientation = random.choice([Protocole.HORIZONTAL, Protocole.VERTICAL])

            bateau = Bateau(nom, taille)
            if self.placer_bateau(bateau, x, y, orientation):
                return True

        return False

    def placer_bateau(self, bateau, x, y, orientation):
        """
        Place un bateau sur la grille

        Returns:
            True si le placement a réussi, False sinon
        """
        if not self.placement_valide(bateau, x, y, orientation):
            return False

        # Positionner le bateau
        bateau.positionner(x, y, orientation)

        # Marquer les cases sur la grille
        for coord_x, coord_y in bateau.obtenir_coordonnees():
            self.grille[coord_y][coord_x] = Protocole.CASE_BATEAU

        return True

    def placer_bateaux_aleatoire(self):
        """Place tous les bateaux de manière aléatoire"""
        for bateau in self.bateaux:
            place = False
            tentatives = 0
            max_tentatives = 1000

            while not place and tentatives < max_tentatives:
                x = random.randint(0, Protocole.TAILLE_GRILLE - 1)
                y = random.randint(0, Protocole.TAILLE_GRILLE - 1)
                orientation = random.choice([Protocole.HORIZONTAL, Protocole.VERTICAL])

                if self.placer_bateau(bateau, x, y, orientation):
                    print(f"Bateau {self.nom} : x = {x}, y = {y}")
                    place = True

                tentatives += 1

            if not place:
                raise Exception(f"Impossible de placer le bateau {bateau.nom}")

    def recevoir_tir(self, x, y):
        """
        Traite un tir reçu

        Returns:
            Tuple (résultat, bateau_coulé)
            résultat: RATE, TOUCHE ou COULE
            bateau_coulé: nom du bateau si coulé, None sinon
        """
        if not Protocole.valider_coordonnees(x, y):
            return Protocole.TIR_RATE, None

        # Vérifier si la case contient un bateau
        if self.grille[y][x] != Protocole.CASE_BATEAU:
            self.grille[y][x] = Protocole.CASE_RATE
            return Protocole.TIR_RATE, None

        # Marquer la case comme touchée
        self.grille[y][x] = Protocole.CASE_TOUCHE

        # Trouver quel bateau a été touché
        bateau_touche = None
        for bateau in self.bateaux:
            if bateau.est_touche(x, y):
                bateau_touche = bateau
                break

        # Vérifier si le bateau est coulé
        if bateau_touche and bateau_touche.est_coule():
            return Protocole.TIR_COULE, bateau_touche.nom

        return Protocole.TIR_TOUCHE, None

    def enregistrer_tir(self, x, y, resultat):
        """Enregistre le résultat d'un tir effectué sur la grille de suivi"""
        if resultat == Protocole.TIR_RATE:
            self.grille_suivi[y][x] = Protocole.CASE_RATE
        else:  # TOUCHE ou COULE
            self.grille_suivi[y][x] = Protocole.CASE_TOUCHE

    def tous_bateaux_coules(self):
        """Vérifie si tous les bateaux du joueur sont coulés"""
        return all(bateau.est_coule() for bateau in self.bateaux)

    def afficher_grille(self, afficher_bateaux=True):
        """Affiche la grille du joueur"""
        print(f"\n=== Grille de {self.nom} ===")
        print("   ", end="")
        for i in range(Protocole.TAILLE_GRILLE):
            print(f" {i} ", end="")
        print()

        for y in range(Protocole.TAILLE_GRILLE):
            print(f" {y} ", end="")
            for x in range(Protocole.TAILLE_GRILLE):
                case = self.grille[y][x]
                if case == Protocole.CASE_EAU:
                    print(" ~ ", end="")
                elif case == Protocole.CASE_BATEAU:
                    print(" B " if afficher_bateaux else " ~ ", end="")
                elif case == Protocole.CASE_TOUCHE:
                    print(" X ", end="")
                elif case == Protocole.CASE_RATE:
                    print(" O ", end="")
            print()

    def afficher_grille_suivi(self):
        """Affiche la grille de suivi des tirs"""
        print(f"\n=== Tirs de {self.nom} ===")
        print("   ", end="")
        for i in range(Protocole.TAILLE_GRILLE):
            print(f" {i} ", end="")
        print()

        for y in range(Protocole.TAILLE_GRILLE):
            print(f" {y} ", end="")
            for x in range(Protocole.TAILLE_GRILLE):
                case = self.grille_suivi[y][x]
                if case == Protocole.CASE_EAU:
                    print(" ~ ", end="")
                elif case == Protocole.CASE_TOUCHE:
                    print(" X ", end="")
                elif case == Protocole.CASE_RATE:
                    print(" O ", end="")
            print()

    def obtenir_positions_bateaux(self):
        """
        Retourne les positions de tous les bateaux pour sérialisation

        Returns:
            Liste de dictionnaires avec les infos de chaque bateau
        """
        positions = []
        for bateau in self.bateaux:
            if bateau.positionne:
                positions.append({
                    "nom": bateau.nom,
                    "taille": bateau.taille,
                    "x": bateau.x,
                    "y": bateau.y,
                    "orientation": bateau.orientation
                })
        return positions

    def placer_bateaux_depuis_positions(self, positions):
        """
        Place les bateaux à partir d'une liste de positions

        Args:
            positions: Liste de dict avec les positions des bateaux

        Returns:
            True si tous les bateaux ont été placés, False sinon
        """
        # Réinitialiser les bateaux
        self.bateaux = []
        self.grille = [[Protocole.CASE_EAU for _ in range(Protocole.TAILLE_GRILLE)]
                       for _ in range(Protocole.TAILLE_GRILLE)]

        # Placer chaque bateau
        for pos in positions:
            bateau = Bateau(pos["nom"], pos["taille"])
            if not self.placer_bateau(bateau, pos["x"], pos["y"], pos["orientation"]):
                return False
            self.bateaux.append(bateau)

        return True

    def afficher_bateaux(self):
        """Affiche l'état de tous les bateaux"""
        print(f"\n=== Bateaux de {self.nom} ===")
        for bateau in self.bateaux:
            print(f"  {bateau}")