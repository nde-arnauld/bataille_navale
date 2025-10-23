from joueur import Joueur

class Partie:
    def __init__(self, joueur1: Joueur, joueur2: Joueur):
        self.joueur1 = joueur1
        self.joueur2 = joueur2
        self.tour_actuel = joueur1
        self.en_cours = True

    def changer_tour(self):
        """Change le joueur courant"""
        self.tour_actuel = self.joueur1 if self.tour_actuel == self.joueur2 else self.joueur2

    def tirer(self, pos: tuple) -> str:
        """Applique un tir sur l’adversaire"""
        cible = self.joueur2 if self.tour_actuel == self.joueur1 else self.joueur1
        resultat = cible.recevoir_tir(pos)
        print(f"{self.tour_actuel.nom} tire sur {pos} → {resultat}")

        if cible.a_perdu():
            self.en_cours = False
            print(f"\n{self.tour_actuel.nom} a gagné la partie !")
        else:
            self.changer_tour()

        return resultat

