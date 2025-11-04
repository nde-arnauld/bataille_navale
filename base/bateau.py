from reseau.protocole import Protocole

class Bateau:
    def __init__(self, nom, taille, x=None, y=None, orientation=None):
        """
        Initialise un bateau

        Args:
            nom: Nom du bateau
            taille: Taille du bateau (nombre de cases)
            x: Coordonnée x de départ
            y: Coordonnée y de départ
            orientation: 'H' pour horizontal, 'V' pour vertical
        """
        self.nom = nom
        self.taille = taille
        self.x = x
        self.y = y
        self.orientation = orientation
        self.cases_touchees = set()  # Ensemble des positions touchées
        self.positionne = False

    def positionner(self, x, y, orientation):
        """Positionne le bateau sur la grille"""
        self.x = x
        self.y = y
        self.orientation = orientation
        self.positionne = True

    def obtenir_coordonnees(self):
        """Retourne la liste de toutes les coordonnées occupées par le bateau"""
        if not self.positionne:
            return []

        coordonnees = []
        for i in range(self.taille):
            if self.orientation == Protocole.HORIZONTAL:
                coordonnees.append((self.x + i, self.y))
            else:  # VERTICAL
                coordonnees.append((self.x, self.y + i))
        return coordonnees

    def est_touche(self, x, y):
        """
        Vérifie si le tir touche ce bateau et enregistre le coup

        Returns :
            True si le bateau est touché, False sinon
        """
        coordonnees = self.obtenir_coordonnees()
        if (x, y) in coordonnees:
            self.cases_touchees.add((x, y))
            return True
        return False

    def est_coule(self):
        """Vérifie si le bateau est complètement coulé"""
        return len(self.cases_touchees) == self.taille

    def __str__(self):
        """Représentation textuelle du bateau"""
        etat = "coulé" if self.est_coule() else f"{len(self.cases_touchees)}/{self.taille} touché"
        return f"{self.nom} ({self.taille} cases) - {etat}"