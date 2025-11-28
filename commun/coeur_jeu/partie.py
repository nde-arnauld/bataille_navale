from commun import constantes as const
from .joueur import Joueur
from typing import Any

from ..constantes import NOM_SERVEUR


class Partie:
    def __init__(self, joueur1: Joueur, joueur2: Joueur=None, etat: str = const.ETAT_EN_ATTENTE, est_tour_joueur1: bool = True, gagnant: str = None):
        """
        Initialise une partie. Utilisé pour la création et la reprise.

        Args:
            joueur1: Premier joueur (client)
            joueur2: Deuxième joueur (serveur ou autre client)
            etat: État initial de la partie (pour la reprise)
            est_tour_joueur1: Indicateur de tour (pour la reprise)
            gagnant: Nom du gagnant (pour la reprise)
        """
        self.joueur1 = joueur1
        self.joueur2 = joueur2 if joueur2 else Joueur(NOM_SERVEUR)
        self.etat = etat
        self.est_tour_joueur1 = est_tour_joueur1
        self.gagnant = gagnant

    def demarrer(self) -> None:
        """
        Démarre la partie en positionnant les navires et en modifiant l'état de la partie.

        Cette méthode :
            * Vérifie si tous les navires de chaque joueur sont placés,
              et les place aléatoirement si nécessaire.
            * Met l'attribut d'état de la partie à 'EN_COURS'.
        """
        # S'assurer que les navires sont placés
        if not all(n.positionne for n in self.joueur1.navires):
            self.joueur1.placer_navires_aleatoire()

        if not all(n.positionne for n in self.joueur2.navires):
            self.joueur2.placer_navires_aleatoire()

        self.etat = const.ETAT_EN_COURS

    def traiter_tir(self, x: int, y: int) -> tuple[str|None, str|None, bool]:
        """
        Traite un tir du joueur actif

        Args:
            x: Coordonnée x du tir
            y: Coordonnée y du tir

        Returns:
            Tuple (resultat, navire_coule, partie_terminee)
        """
        if self.etat != const.ETAT_EN_COURS:
            return const.MSG_ERREUR, "Partie non en cours", False

        # Déterminer qui tire et qui reçoit
        cible = self.joueur2 if self.est_tour_joueur1 else self.joueur1
        tireur = self.joueur1 if self.est_tour_joueur1 else self.joueur2

        # 1. Effectuer le tir
        resultat, navire_coule = cible.recevoir_tir(x, y)

        # Si le tir n'est pas "déjà tiré" (TIR_DEJA_TIRE), on met à jour la grille de suivi et on passe le tour.
        if resultat != const.TIR_DEJA_TIRE:
            # 2. Enregistrer le tir dans la grille de suivi du tireur
            tireur.enregistrer_tir(x, y, resultat)

            # Vérifier si la partie est terminée
            if cible.tous_navires_coules():
                self.etat = const.ETAT_TERMINEE
                self.gagnant = tireur.nom
                return resultat, navire_coule, True

            # 4. Changer de tour
            self.est_tour_joueur1 = not self.est_tour_joueur1

        return resultat, navire_coule, False

    def initialiser_joueur_ia(self) -> None:
        """
        Crée et configure le Joueur 2 (l'IA) si la partie est en mode Solo.
        """
        if self.joueur2 is None or self.joueur2.nom == NOM_SERVEUR:
            self.joueur2 = Joueur(NOM_SERVEUR)

    def abandonner(self, joueur_abandonne: str) -> None:
        """
        Déclare l'abandon d'un joueur.

        Met l'état de la partie à "abandonnée", et définit l'autre joueur comme gagnant.

        Args:
            joueur_abandonne: Nom du joueur qui abandonne.
        """
        self.etat = const.ETAT_ABANDONNEE
        if joueur_abandonne == self.joueur1.nom:
            self.gagnant = self.joueur2.nom
        else:
            self.gagnant = self.joueur1.nom

    def est_terminee(self) -> bool:
        """
        Vérifie si la partie est terminée (victoire ou abandon).

        Returns:
            bool: True si la partie est terminée, False autrement.
        """
        return self.etat in [const.ETAT_TERMINEE, const.ETAT_ABANDONNEE]

    def obtenir_gagnant(self) -> str | None:
        """
        Retourne le nom du joueur gagnant. Renvoie None si la partie n'est pas terminée.

        Returns:
            str or None: nom du gagnant, ou None si pas de gagnant.
        """
        return self.gagnant

    def obtenir_etat(self) -> str:
        """
        Retourne l'état actuel de la partie.

        Returns:
            str: état actuel (voir const).
        """
        return self.etat

    def __str__(self) -> str:
        """
        Retourne une chaîne de caractères représentant la partie.

        Returns:
            str: Représentation de la partie (j1, j2, tour j1, état).
        """
        return f"j1: {self.joueur1.nom} | j2: {self.joueur2.nom} | tour j1: {self.est_tour_joueur1} | etat: {self.etat}"

    def to_dict(self) -> dict[str, Any]:
        """ Sérialise l'état complet de la partie pour la sauvegarde JSON. """
        return {
            "joueur1": self.joueur1.to_dict(),  # Utilise la sérialisation de Joueur
            "joueur2": self.joueur2.to_dict(),
            "etat": self.etat,
            "tour_joueur1": self.est_tour_joueur1,
            "gagnant": self.gagnant
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> 'Partie':
        """ Désérialise et crée un objet Partie à partir d'un dictionnaire JSON. """
        # Utilise la désérialisation statique de Joueur pour reconstruire les objets Joueur
        joueur1 = Joueur.from_dict(data["joueur1"])
        joueur2 = Joueur.from_dict(data["joueur2"])

        return Partie(
            joueur1=joueur1,
            joueur2=joueur2,
            etat=data["etat"],
            est_tour_joueur1=data["tour_joueur1"],
            gagnant=data["gagnant"]
        )