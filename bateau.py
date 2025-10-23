class Bateau:
    def __init__(self, nom: str, taille: int, orientation: str = "H"):
        """
        orientation : 'H' pour horizontal, 'V' pour vertical
        """
        self.nom = nom
        self.taille = taille
        self.orientation = orientation.upper()
        self.positions = []       # liste de tuples (x, y)
        self.touchees = []        # cases touchées

    def placer(self, debut: tuple):
        """
        Calcule automatiquement les positions du bateau à partir
        d'une position de départ et de l'orientation.
        """
        x, y = debut
        self.positions = []
        for i in range(self.taille):
            if self.orientation == "H":
                self.positions.append((x, y + i))
            else:
                self.positions.append((x + i, y))

    def est_touchee(self, pos: tuple) -> bool:
        """Marque la position comme touchée si elle appartient au bateau"""
        if pos in self.positions and pos not in self.touchees:
            self.touchees.append(pos)
            return True
        return False

    def est_coule(self) -> bool:
        """Retourne True si toutes les positions du bateau sont touchées"""
        return len(self.touchees) == len(self.positions)
