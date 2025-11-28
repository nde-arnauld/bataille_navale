import random

from commun import constantes as const
from .navire import Navire
from typing import Any

class Joueur:
    def __init__(self, nom: str="Joueur", grille: list[list[int]] = None, grille_suivi: list[list[int]] = None, navires: list[Navire] = None):
        """
        Initialise un joueur avec ses grilles

        Args:
            nom: Nom du joueur
        """
        self.nom = nom
        # Grille principale (où sont placés les navires du joueur)
        self.grille = grille if grille is not None else Joueur._creer_grille_vide()

        # Grille de suivi (pour tracer les tirs effectués sur l'adversaire)
        self.grille_suivi = grille_suivi if grille_suivi is not None else Joueur._creer_grille_vide()

        # Liste des navires
        self.navires = navires if navires is not None else []
        if not self.navires:
            self._initialiser_navires()

    @staticmethod
    def _creer_grille_vide() -> list[list[int]]:
        """ Crée une grille vide 10x10. """
        return [[const.CASE_EAU for _ in range(const.TAILLE_GRILLE)]
                for _ in range(const.TAILLE_GRILLE)]

    def _initialiser_navires(self) -> None:
        """
        Initialise la liste des navires selon le protocole.

        Cette méthode parcourt la liste des navires définie dans le protocole (const.NAVIRES),
        qui contient des tuples (nom, taille) pour chaque type de navire du jeu.
        Pour chaque navire, elle crée une instance de Navire avec le nom et la taille fournis,
        puis ajoute cette instance à la liste des navires du joueur (self.navires).

        Cela permet de préparer tous les navires requis pour une partie, en respectant les règles
        du jeu et la configuration standard définie par le protocole.
        """
        for nom, taille in const.NAVIRES:
            self.navires.append(Navire(nom, taille))

    def placement_valide(self, navire: Navire, x: int, y: int, orientation: str) -> bool:
        """
        Vérifie si le placement d'un navire est valide

        Args:
            navire: Le navire à placer.
            x: La coordonnée x de départ du navire.
            y: La coordonnée y de départ du navire.
            orientation: L'orientation du navire ('H' pour horizontal, 'V' pour vertical).

        Returns:
            bool: True si le placement est valide, False sinon
        """
        # Vérifier que le navire ne dépasse pas de la grille
        if orientation == const.HORIZONTAL:
            if x + navire.taille > const.TAILLE_GRILLE:
                return False
        else:  # VERTICAL
            if y + navire.taille > const.TAILLE_GRILLE:
                return False

        # Vérifier qu'aucune case n'est déjà occupée
        for i in range(navire.taille):
            pos_x = x + i if orientation == const.HORIZONTAL else x
            pos_y = y if orientation == const.HORIZONTAL else y + i

            if self.grille[pos_y][pos_x] != const.CASE_EAU:
                return False

        return True

    def placer_navire(self, navire: Navire, x: int, y: int, orientation: str) -> bool:
        """
        Tente de placer un navire sur la grille à la position (x, y) avec l'orientation donnée.

        Args:
            navire (Navire): Le navire à placer
            x (int): Abscisse de départ du navire
            y (int): Ordonnée de départ du navire
            orientation (str): 'H' pour horizontal, 'V' pour vertical.

        Returns:
            bool: True si le placement est possible (hors collision et dans la grille),
                  False sinon.
        """
        if not self.placement_valide(navire, x, y, orientation):
            return False

        # Positionner le navire
        navire.positionner(x, y, orientation)

        # Marquer les cases sur la grille
        for coord_x, coord_y in navire.obtenir_coordonnees():
            self.grille[coord_y][coord_x] = const.CASE_NAVIRE

        return True

    def recevoir_tir(self, x: int, y: int) -> tuple[str, str | None]:
        """
        Traite un tir reçu sur la grille du joueur.

        Args :
            x: Abscisse (colonne) du tir.
            y: Ordonnée (ligne) du tir.

        Returns :
            tuple[str, str | None]:
                * résultat (str) : Résultat du tir, parmi :
                    * const.TIR_RATE (tir dans l'eau ou hors grille)
                    * const.TIR_TOUCHE (navire touché, mais pas coulé)
                    * const.TIR_COULE (navire touché et coulé)
                * navire_coulé (str | None) : nom du navire coulé si applicable,
                  sinon None.

        Le tir est enregistré sur la grille : la case visée est marquée comme touchée
        ou ratée selon le cas. Si un navire est touché puis coulé entièrement,
        son nom est retourné dans navire_coulé.
        """
        # 1. Vérification des limites de la grille
        if not (0 <= x < const.TAILLE_GRILLE and 0 <= y < const.TAILLE_GRILLE):
            return const.TIR_RATE, None

        etat_actuel = self.grille[y][x]

        # 2. Vérification des tirs redondants
        if etat_actuel == const.CASE_TOUCHE or etat_actuel == const.CASE_RATE:
            return const.TIR_DEJA_TIRE, None

            # 3. Tir dans l'eau
        if etat_actuel == const.CASE_EAU:
            self.grille[y][x] = const.CASE_RATE
            return const.TIR_RATE, None

        # 4. Tir sur un navire (CASE_NAVIRE)
        if etat_actuel == const.CASE_NAVIRE:
            self.grille[y][x] = const.CASE_TOUCHE  # Marquer la case comme touchée

            navire_touche = None
            for navire in self.navires:
                # La méthode navire.est_touche met à jour le set cases_touchees interne
                if navire.est_touche(x, y):
                    navire_touche = navire
                    break

            if navire_touche and navire_touche.est_coule():
                return const.TIR_COULE, navire_touche.nom

            return const.TIR_TOUCHE, None

        return const.TIR_RATE, None  # Cas par défaut

    def _placer_navire_aleatoire_unique(self, nom: str, taille: int) -> bool:
        """
        Tente de placer un navire de nom et taille donnés aléatoirement sur la grille.

        Args:
            nom: Le nom du navire à placer.
            taille: La taille du navire à placer.

        Returns:
            bool: True si le placement a réussi, False si impossible après 1000 essais.
        """
        for _ in range(1000):
            x = random.randint(0, const.TAILLE_GRILLE - 1)
            y = random.randint(0, const.TAILLE_GRILLE - 1)
            orientation = random.choice([const.HORIZONTAL, const.VERTICAL])

            navire = Navire(nom, taille)
            if self.placer_navire(navire, x, y, orientation):
                return True

        return False

    def placer_navires_aleatoire(self) -> None | Exception:
        """
        Place tous les navires du joueur aléatoirement sur la grille.

        Pour chaque navire de self.navires, tente de le placer aléatoirement
        (position et orientation).

        Raises:
            Exception: Si un des navires ne peut pas être placé après 1000 essais.
        """
        for navire in self.navires:
            place = False
            tentatives = 0
            max_tentatives = 1000

            while not place and tentatives < max_tentatives:
                x = random.randint(0, const.TAILLE_GRILLE - 1)
                y = random.randint(0, const.TAILLE_GRILLE - 1)
                orientation = random.choice([const.HORIZONTAL, const.VERTICAL])

                if self.placer_navire(navire, x, y, orientation):
                    print(f"Navire {self.nom} : x = {x}, y = {y}")
                    place = True

                tentatives += 1

            if not place:
                raise Exception(f"Impossible de placer le navire {navire.nom}")

    def tous_navires_coules(self) -> bool:
        """
        Permet de vérifier si tous les navires du joueur sont coulés.

        Returns:
            bool: True si tous les navires sont coulés, False sinon.
        """
        return all(navire.est_coule() for navire in self.navires)



    def enregistrer_tir(self, x: int, y: int, resultat: str) -> None:
        """
        Met à jour la grille de suivi du joueur après un tir.

        Paramètres :
            x: Abscisse visée.
            y: Ordonnée visée.
            resultat: Résultat du tir (TIR_RATE, TIR_TOUCHE ou TIR_COULE).

        Marque la case tirée comme touchée (X) ou ratée (O) selon le résultat.
        """
        if resultat == const.TIR_RATE:
            self.grille_suivi[y][x] = const.CASE_RATE
        else:  # TOUCHE ou COULE
            self.grille_suivi[y][x] = const.CASE_TOUCHE

    def to_dict(self) -> dict[str, Any]:
        """ Sérialise l'état complet du joueur pour la sauvegarde JSON. """
        return {
            "nom": self.nom,
            "grille": self.grille,
            "grille_suivi": self.grille_suivi,
            "navires": [navire.to_dict() for navire in self.navires]  # Utilise la méthode de Navire
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> 'Joueur':
        """ Désérialise et crée un objet Joueur à partir d'un dictionnaire JSON. """
        navires = [Navire.from_dict(d) for d in data["navires"]]

        return Joueur(
            nom=data["nom"],
            grille=data["grille"],
            grille_suivi=data["grille_suivi"],
            navires=navires
        )

    def afficher_grille(self, afficher_navires: bool = True) -> None:
        """
        Affiche la grille du joueur dans la console.

        Args:
            afficher_navires: Affiche les navires sur la grille si True, sinon affiche uniquement l'eau 
            et les résultats des tirs (pour masquer la position des navires à l'adversaire).

        La grille montre :
            ~ : case d'eau
            B : case avec un navire (affiché seulement si afficher_navires est True)
            X : navire touché
            O : tir raté (case déjà visée, sans navire).
        """

        print(f"\n=== Grille de {self.nom} ===")
        print("   ", end="")
        for i in range(const.TAILLE_GRILLE):
            print(f" {i} ", end="")
        print()

        for y in range(const.TAILLE_GRILLE):
            print(f" {y} ", end="")
            for x in range(const.TAILLE_GRILLE):
                case = self.grille[y][x]
                if case == const.CASE_EAU:
                    print(" ~ ", end="")
                elif case == const.CASE_NAVIRE:
                    print(" B " if afficher_navires else " ~ ", end="")
                elif case == const.CASE_TOUCHE:
                    print(" X ", end="")
                elif case == const.CASE_RATE:
                    print(" O ", end="")
            print()

    def afficher_grille_suivi(self) -> None:
        """
        Affiche la grille de suivi des tirs dans la console.

        La grille de suivi montre :
            ~ : case d'eau
            X : navire touché
            O : tir raté (case déjà visée, sans navire).
        """
        print(f"\n=== Tirs de {self.nom} ===")
        print("   ", end="")
        for i in range(const.TAILLE_GRILLE):
            print(f" {i} ", end="")
        print()

        for y in range(const.TAILLE_GRILLE):
            print(f" {y} ", end="")
            for x in range(const.TAILLE_GRILLE):
                case = self.grille_suivi[y][x]
                if case == const.CASE_EAU:
                    print(" ~ ", end="")
                elif case == const.CASE_TOUCHE:
                    print(" X ", end="")
                elif case == const.CASE_RATE:
                    print(" O ", end="")
            print()

    def obtenir_positions_navires(self) -> list[dict[str, str|int]]:
        """
        Retourne les positions de tous les navires pour sérialisation.

        Returns:
            list[dict[str, any]]: Liste de dictionnaires avec les infos de chaque navire.
        """
        positions = []
        for navire in self.navires:
            if navire.positionne:
                positions.append({
                    "nom": navire.nom,
                    "taille": navire.taille,
                    "x": navire.x,
                    "y": navire.y,
                    "orientation": navire.orientation
                })
        return positions

    def placer_navires_depuis_positions(self, positions: list[dict[str, str|int]]) -> bool:
        """
        Place les navires à partir d'une liste de positions.

        Args:
            positions: Liste de dictionnaires avec les positions des navires.

        Returns:
            bool: True si tous les navires ont été placés, False sinon.
        """
        # Réinitialiser les navires
        self.navires = []
        self.grille = [[const.CASE_EAU for _ in range(const.TAILLE_GRILLE)]
                       for _ in range(const.TAILLE_GRILLE)]

        # Placer chaque navire
        for pos in positions:
            navire = Navire(pos["nom"], pos["taille"])
            if not self.placer_navire(navire, pos["x"], pos["y"], pos["orientation"]):
                return False
            self.navires.append(navire)

        return True

    def afficher_navires(self) -> None:
        """
        Affiche un résumé de l'état de tous les navires du joueur.

        Cette méthode affiche pour chaque navire son nom, sa taille et son état courant
        (nombre de cases touchées sur la taille totale ou 'coulé' si le navire est complètement détruit).
        """
        print(f"\n=== Navires de {self.nom} ===")
        for navire in self.navires:
            print(f"  {navire}")

    def __str__(self):
        # Compte le nombre de navires qui sont coulés
        navires_coules = sum(1 for navire in self.navires if navire.est_coule())
        total_navires = len(self.navires)

        return f"Joueur: {self.nom} | Statut: {navires_coules}/{total_navires} navires coulés."

    def afficher_etat_complet(self):
        """Affiche le nom du joueur, l'état de la flotte et les deux grilles."""

        print("\n" + "=" * 40)
        print(self.__str__())  # Utilise la méthode __str__ pour le résumé
        print("-" * 40)

        # 1. Affichage de la grille principale (ses propres navires)
        print("\n--- GRILLE PRINCIPALE (MES NAVIRES) ---")
        self.afficher_grille(afficher_navires=True)

        # 2. Affichage de la grille de suivi (ses tirs sur l'adversaire)
        print("\n--- GRILLE DE SUIVI (TIRS ADVERSES) ---")
        self.afficher_grille_suivi()

        # 3. Affichage de l'état détaillé des navires
        self.afficher_navires()  # Supposons que cette méthode affiche chaque navire.

        print("=" * 40)