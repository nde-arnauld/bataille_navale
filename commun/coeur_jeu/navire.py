from commun.constantes import HORIZONTAL

class Navire:
    def __init__(self, nom: str, taille: int, x: int=0, y: int=0, orientation: str=None):
        """
        Initialise un navire

        Args:
            nom: Nom du navire
            taille: Taille du navire (nombre de cases)
            x: Coordonnée x de départ
            y: Coordonnée y de départ
            orientation: 'H' pour horizontal, 'V' pour vertical
        """
        self.nom:str = nom
        self.taille = taille
        self.x = x
        self.y = y
        self.orientation = orientation if orientation is not None else HORIZONTAL
        self.cases_touchees: set[tuple[int, int]] = set()  # Ensemble des positions touchées
        self.positionne = False

    def positionner(self, x: int, y: int, orientation: str) -> None:
        """
        Positionne le navire sur la grille.

        Args:
            x: La coordonnée x de départ du navire.
            y: La coordonnée y de départ du navire.
            orientation: L'orientation du navire ('H' pour horizontal, 'V' pour vertical).

        Cette méthode place le navire à la position donnée sur la grille avec l'orientation spécifiée.
        Elle met également à jour l'attribut 'positionne' du navire à True.
        """
        self.x = x
        self.y = y
        self.orientation = orientation
        self.positionne = True

    def obtenir_coordonnees(self) -> list[tuple[int, int]]:
        """
        Retourne la liste de toutes les coordonnées occupées par le navire.

        Cette méthode calcule l'ensemble des cases (sous forme de tuples (x, y)) que le navire occupe
        sur la grille en fonction de sa position de départ (self.x, self.y), de sa taille (self.taille)
        et de son orientation (self.orientation). Si le navire n'a pas encore été positionné 
        (c'est-à-dire self.positionne est False), la méthode retourne une liste vide.

        Returns:
            list of tuple: Liste de coordonnées (x, y) occupées par le navire.
        """
        if not self.positionne:
            return []

        coordonnees = []
        for i in range(self.taille):
            if self.orientation == HORIZONTAL:
                coordonnees.append((self.x + i, self.y))
            else:  # VERTICAL
                coordonnees.append((self.x, self.y + i))
        return coordonnees

    def est_touche(self, x: int, y: int) -> bool:
        """
        Vérifie si le tir touche ce navire et enregistre le coup.

        Cette méthode permet de déterminer si un tir portant sur la case (x, y) touche 
        ce navire. Si le tir touche, la position du tir est ajoutée à l'ensemble des cases touchées 
        du navire ('self.cases_touchees'). Sinon, rien n'est modifié.

        Args:
            x: La coordonnée x du tir.
            y: La coordonnée y du tir.

        Returns:
            bool: True si le navire est touché (le tir touche au moins une case occupée par ce navire),
                  False sinon.
        """
        if (x, y) in self.obtenir_coordonnees():
            self.cases_touchees.add((x, y))
            return True
        return False

    def est_coule(self) -> bool:
        """
        Vérifie si le navire est complètement coulé.

        Returns:
            bool: True si le nombre de cases touchées équivaut à la taille du navire, 
                  False sinon.
        """
        return len(self.cases_touchees) == self.taille

    def to_dict(self) -> dict:
        """
        Convertit l'objet en dictionnaire (listes pour les coordonnées touchées) pour l'écriture JSON.

        Returns:
             Un objet json.
        """
        return {
            "nom": self.nom,
            "taille": self.taille,
            "x": self.x,
            "y": self.y,
            "orientation": self.orientation,
            "cases_touchees": list(self.cases_touchees),
            "positionne": self.positionne,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Navire':
        navire = Navire(data["nom"],
                        data["taille"],
                        data["x"],
                        data["y"],
                        data["orientation"])
        navire.cases_touchees = set(tuple(c) for c in data.get("cases_touchees", []))
        navire.positionne = data.get("positionne", False)
        return navire

    def __str__(self) -> str:
        """
        Représentation textuelle du navire.

        Returns:
            str: Représentation textuelle du navire.
        """
        etat = "coulé" if self.est_coule() else f"{len(self.cases_touchees)}/{self.taille} touché"
        return f"{self.nom} ({self.taille} cases) - {etat}"