from bateau import Bateau
from constantes import *


class Joueur:
    def __init__(self, nom: str):
        self.nom = nom
        self.matrice = [[CASE_VIDE for _ in range(10)] for _ in range(10)]  # 0 = vide
        self.bateaux = []
        self.tirs_effectues = []  # positions déjà tirées

    def peut_placer(self, bateau: Bateau, debut: tuple) -> bool:
        """Vérifie si le bateau peut être placé sans sortir ni chevaucher"""

        x, y = debut
        if bateau.orientation == "H":
            if y + bateau.taille > 10:
                return False
            positions = [(x, y + i) for i in range(bateau.taille)]
        else:
            if x + bateau.taille > 10:
                return False
            positions = [(x + i, y) for i in range(bateau.taille)]

        # Vérifie que les cases sont libres
        return all(self.matrice[xi][yi] == CASE_VIDE for xi, yi in positions)

    def placer_bateau(self, bateau: Bateau, debut: tuple):
        """Place un bateau automatiquement selon son orientation"""

        if not self.peut_placer(bateau, debut):
            raise ValueError("Impossible de placer le bateau ici !")

        bateau.placer(debut)
        for (x, y) in bateau.positions:
            self.matrice[x][y] = CASE_BATEAU
        self.bateaux.append(bateau)

    def recevoir_tir(self, pos: tuple) -> str:
        """Reçoit un tir et renvoie le résultat ('raté', 'touché', 'coulé')"""

        x, y = pos
        if self.matrice[x][y] == CASE_VIDE:
            self.matrice[x][y] = CASE_TIR_RATE  # raté
            return "raté"
        elif self.matrice[x][y] == CASE_BATEAU:
            self.matrice[x][y] = CASE_BATEAU_TOUCHE  # touché
            for bateau in self.bateaux:
                if bateau.est_touchee(pos):
                    if bateau.est_coule():
                        return f"coulé ({bateau.nom})"
                    return "touché"
        return "déjà tiré"

    def a_perdu(self) -> bool:
        """Retourne True si tous les bateaux sont coulés"""

        return all(bateau.est_coule() for bateau in self.bateaux)

    def afficher_grille(self):
        """Affiche la grille du joueur avec les symboles simplifiés"""

        symboles = {CASE_VIDE: '_', CASE_BATEAU: 'B', CASE_BATEAU_TOUCHE: 'X', CASE_TIR_RATE: 'O'}
        print(f"\nGrille de {self.nom}:")
        for ligne in self.matrice:
            print(" ".join(symboles.get(x, '?') for x in ligne))

    def afficher_grille_publique(self):
        """Affiche la grille visible par l’adversaire (cache les bateaux non touchés)"""

        symboles = {CASE_VIDE: '_', CASE_BATEAU: '_', CASE_BATEAU_TOUCHE: 'X', CASE_TIR_RATE: 'O'}
        print(f"\nGrille vue par l’adversaire ({self.nom}):")
        for ligne in self.matrice:
            print(" ".join(symboles.get(x, '?') for x in ligne))