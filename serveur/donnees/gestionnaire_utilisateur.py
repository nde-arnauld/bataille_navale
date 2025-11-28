import json
import hashlib
import os
from typing import Any

from commun import constantes as const
from commun.coeur_jeu.partie import Partie


class GestionnaireUtilisateur:
    """
    Gère la persistance des données utilisateur (hashs de mot de passe) et des parties
    sauvegardées via un fichier JSON sur le serveur.
    """

    def __init__(self, chemin_fichier: str):
        self.chemin_fichier = chemin_fichier
        self.data: dict[str, Any] = self._charger_donnees()

    def _charger_donnees(self) -> dict[str, Any]:
        """ Charge le fichier JSON ou initialise une structure vide. """
        if os.path.exists(self.chemin_fichier):
            with open(self.chemin_fichier, 'r', encoding=const.ENCODAGE) as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print(f"Erreur de décodage JSON dans {self.chemin_fichier}. Fichier de données réinitialisé.")

        # Structure initiale
        return {"utilisateurs": {}}

    def _sauvegarder_donnees(self) -> None:
        """ Sauvegarde l'état actuel de self.data dans le fichier JSON. """
        # Écrit de manière indentée pour la lisibilité
        with open(self.chemin_fichier, 'w', encoding=const.ENCODAGE) as f:
            json.dump(self.data, f, indent=4)


    @staticmethod
    def _crypter_mdp(mot_de_passe: str) -> str:
        """
        Crypte un mot de passe en utilisant SHA-256 (standard hashlib).
        """
        # Utilise l'encodage défini dans les constantes
        hash_objet = hashlib.sha256(mot_de_passe.encode(const.ENCODAGE))
        return hash_objet.hexdigest()

    @staticmethod
    def _verifier_mdp(mdp_clair: str, mdp_crypte: str) -> bool:
        """
        Vérifie si le mot de passe en clair correspond au hash stocké.
        """
        return GestionnaireUtilisateur._crypter_mdp(mdp_clair) == mdp_crypte

    # --- Authentification (Utilisé par AuthentificationUDP) ---

    def _utilisateur_existe(self, nom: str) -> bool:
        """ Vérifie si un utilisateur existe dans la base de données. """
        return nom in self.data["utilisateurs"]

    def enregistrer_utilisateur(self, nom: str, mdp: str) -> bool:
        """
        Crée un nouvel utilisateur.

        Retourne True en cas de succès, False si le nom est déjà pris ou le mdp est invalide.
        """
        if self._utilisateur_existe(nom) or len(mdp) < const.TAILLE_MIN_MDP:
            return False

        mdp_hash = GestionnaireUtilisateur._crypter_mdp(mdp)

        self.data["utilisateurs"][nom] = {
            "mdp_hash": mdp_hash,
            "partie_sauvegardee": None  # Aucune partie sauvegardée au départ
        }
        self._sauvegarder_donnees()
        return True

    def verifier_authentification(self, nom: str, mdp: str) -> bool:
        """
        Vérifie l'existence et les identifiants de l'utilisateur.

        Retourne True si l'authentification réussit, False sinon.
        """
        if not self._utilisateur_existe(nom):
            return False

        utilisateur = self.data["utilisateurs"][nom]
        mdp_crypte = utilisateur.get("mdp_hash")

        return GestionnaireUtilisateur._verifier_mdp(mdp, mdp_crypte)

    # --- Sauvegarde et Reprise de Partie (Utilisé par GestionnaireClient) ---

    def sauvegarder_partie(self, nom_joueur: str, partie: Partie) -> None:
        """
        Sauvegarde l'état complet de la partie pour un joueur.
        Si la partie est 'EN_COURS', elle est marquée 'MIS_EN_PAUSE' avant la sauvegarde.
        """
        if not self._utilisateur_existe(nom_joueur):
            # Normalement ne devrait pas arriver après l'authentification
            return

        # Mise à jour de l'état si elle est en cours et est sauvegardée
        if partie.etat == const.ETAT_EN_COURS:
            partie.etat = const.ETAT_MIS_EN_PAUSE

        partie_dict = partie.to_dict()

        self.data["utilisateurs"][nom_joueur]["partie_sauvegardee"] = partie_dict
        self._sauvegarder_donnees()

    def charger_partie(self, nom_joueur: str) -> Partie|None:
        """
        Charge la partie sauvegardée pour un joueur et la désérialise.

        Retourne l'objet Partie ou None si aucune partie n'est trouvée.
        """
        if not self._utilisateur_existe(nom_joueur):
            return None

        partie_dict = self.data["utilisateurs"][nom_joueur].get("partie_sauvegardee")

        if partie_dict is None:
            return None

        return Partie.from_dict(partie_dict)

    def partie_existe(self, nom_joueur: str) -> bool:
        """
        Vérifie si une partie mise en pause est disponible pour ce joueur.
        """
        if not self._utilisateur_existe(nom_joueur):
            return False

        return self.data["utilisateurs"][nom_joueur].get("partie_sauvegardee") is not None

    def supprimer_partie_sauvegardee(self, nom_joueur: str) -> None:
        """
        Supprime la référence à la partie sauvegardée (ex: après une victoire/défaite ou reprise).
        """
        if self._utilisateur_existe(nom_joueur):
            self.data["utilisateurs"][nom_joueur]["partie_sauvegardee"] = None
            self._sauvegarder_donnees()